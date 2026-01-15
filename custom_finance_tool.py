import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from langchain.tools import tool

# --- CONFIGURATION ---
# Real API base URL (docs site is https://sofixaca.vercel.app)
BASE_URL = "https://ac-api-server.vercel.app"

try:
    REQUEST_TIMEOUT = float(os.environ.get("AC_API_TIMEOUT", "12"))
except ValueError:
    REQUEST_TIMEOUT = 12.0


# --- Helpers for flexible API schemas ---
def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_present(d: Any, keys: list[str]) -> Any:
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _fmt_num(value: Any, *, prefix: str = "", suffix: str = "", default: str = "N/A") -> str:
    num = _coerce_float(value)
    if num is None:
        return default
    return f"{prefix}{num:,.2f}{suffix}"


def _fmt_int(value: Any, *, default: str = "N/A") -> str:
    try:
        if value is None:
            return default
        return f"{int(value):,d}"
    except (TypeError, ValueError):
        return default


def _fmt_str(value: Any, *, default: str = "N/A") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _get_ac_api_key() -> Optional[str]:
    """Read AC API key from environment.

    Expected header: `x-api-key: <key>`
    """
    return (
        os.environ.get("AC_API_KEY")
        or os.environ.get("AC_API_SERVER_API_KEY")
        or os.environ.get("X_API_KEY")
    )


def _auth_headers() -> Dict[str, str]:
    key = _get_ac_api_key()
    return {"x-api-key": key} if key else {}


@dataclass(frozen=True)
class FetchResult:
    data: Optional[Dict[str, Any]]
    used_url: Optional[str]
    tried_urls: list[str]
    error: Optional[str]


def _candidate_tickers(ticker: str) -> list[str]:
    """Return likely ticker variants (US-style + common India suffixes)."""
    t = (ticker or "").strip()
    if not t:
        return []
    if t.upper() != t:
        t = t.upper()

    # If no suffix is provided, try both NSE/BSE variants.
    # Heuristic: longer tickers (e.g., RELIANCE) are more likely to be Indian symbols
    # where the backend expects `.NS`/`.BO`, while short tickers (e.g., TSLA) may be US.
    candidates: list[str]
    if "." not in t and len(t) > 4:
        candidates = [f"{t}.NS", f"{t}.BO", t]
    elif "." not in t:
        candidates = [t, f"{t}.NS", f"{t}.BO"]
    else:
        candidates = [t]

    # De-dup while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _candidate_paths(ticker: str) -> list[str]:
    """Return API endpoints to try for a given symbol.

    The documented endpoints are under `/server/company/...` and require `x-api-key`.
    """
    t = (ticker or "").strip()
    return [
        f"/server/company/{t}",
        f"/server/company/pnl/{t}",
        f"/server/company/balancesheet/{t}",
    ]


def _unwrap_api_response(payload: Any) -> Any:
    """AC API wraps results in {status,message,data}; return data if present."""
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data")
    return payload


def _fetch_json(path: str, *, params: Optional[Dict[str, Any]] = None) -> tuple[Optional[Any], Optional[str], str]:
    """Fetch a JSON payload from the API.

    Returns: (data, error, used_url)
    - data is unwrapped (payload['data']) if API wrapper is present.
    - error is None on success.
    """
    headers = _auth_headers()
    if not headers:
        return None, "Missing API key. Set AC_API_KEY (used as x-api-key header) before calling /server/* endpoints.", ""

    url = f"{BASE_URL}{path}"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 401:
            return None, "Unauthorized (invalid/missing API key).", url
        if resp.status_code == 404:
            return None, "Not found (endpoint or symbol unsupported).", url
        resp.raise_for_status()
        return _unwrap_api_response(resp.json()), None, url
    except requests.exceptions.RequestException as e:
        return None, str(e), url


def _best_effort_get_latest(path: str, *, params: Optional[Dict[str, Any]] = None) -> tuple[Dict[str, Any], Optional[str], str]:
    data, err, used_url = _fetch_json(path, params=params)
    latest = _pick_latest(data)
    if isinstance(latest, dict):
        return latest, None, used_url
    if isinstance(data, dict):
        return data, None, used_url
    return {}, err, used_url


def _best_effort_get_any(path_candidates: list[str], *, params: Optional[Dict[str, Any]] = None) -> tuple[Optional[Any], Optional[str], Optional[str]]:
    last_err: Optional[str] = None
    last_url: Optional[str] = None
    for path in path_candidates:
        data, err, used_url = _fetch_json(path, params=params)
        last_err, last_url = err, used_url
        if data is not None and err is None:
            return data, None, used_url
    return None, last_err, last_url


def _pick_latest(records: Any) -> Optional[Dict[str, Any]]:
    """Pick the latest record from a list of dicts (by calendarYear then date)."""
    if isinstance(records, list) and records:
        def key_fn(r: Any):
            if not isinstance(r, dict):
                return (-1, "")
            year = r.get("calendarYear")
            try:
                year_num = int(year)
            except (TypeError, ValueError):
                year_num = -1
            date = r.get("date") or ""
            return (year_num, str(date))

        best = max(records, key=key_fn)
        return best if isinstance(best, dict) else None
    if isinstance(records, dict):
        return records
    return None


def fetch_from_api_with_meta(ticker: str) -> FetchResult:
    """Fetch raw JSON for a given ticker, trying common ticker/path variants.

    This protects you from 404s when the backend expects e.g. `RELIANCE.NS` or
    serves data under `/api/stock/...`.
    """
    tried: list[str] = []
    last_err: Optional[str] = None

    headers = _auth_headers()
    if not headers:
        return FetchResult(
            data=None,
            used_url=None,
            tried_urls=[],
            error="Missing API key. Set AC_API_KEY (used as x-api-key header) before calling /server/* endpoints.",
        )

    for t in _candidate_tickers(ticker):
        # Use the main company endpoint as the "exists" check
        url = f"{BASE_URL}/server/company/{t}"
        tried.append(url)
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 401:
                return FetchResult(data=None, used_url=None, tried_urls=tried, error="Unauthorized (invalid/missing API key).")
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            return FetchResult(data=resp.json(), used_url=url, tried_urls=tried, error=None)
        except requests.exceptions.RequestException as e:
            last_err = str(e)
            continue

    # If everything 404'd, provide a helpful error
    if last_err is None:
        hint = ""
        raw = (ticker or "").strip()
        if raw and "." not in raw:
            hint = " Hint: Use exchange suffix like RELIANCE.NS or RELIANCE.BO."
        last_err = f"All candidate URLs returned 404 Not Found.{hint}"
    return FetchResult(data=None, used_url=None, tried_urls=tried, error=last_err)


def fetch_from_api(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch raw JSON for a given ticker from the configured API.

    Returns the parsed JSON dict on success or None on error.
    """
    result = fetch_from_api_with_meta(ticker)
    if result.data is None:
        # Keep prints minimal but actionable
        print(f"API request failed: {result.error}")
    return result.data


def _get_number(data: Dict[str, Any], *keys, default=0.0) -> float:
    """Try multiple key names / nested dicts to extract a numeric value.

    Example: _get_number(data, 'revenue', 'totalRevenue')
    """
    for key in keys:
        # top-level
        v = data.get(key) if isinstance(data, dict) else None
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                continue
    # try common nested containers
    for container in (data.get('data') if isinstance(data, dict) else None,):
        if isinstance(container, dict):
            for key in keys:
                v = container.get(key)
                if v is not None:
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        continue
    if default is None:
        # Caller explicitly wants a sentinel None
        return default  # type: ignore[return-value]
    return float(default)


def analyze_business_health(ticker: str) -> str:
    """Core logic: fetch, map, compute metrics, and return a report string.

    Metrics computed: Inventory Days (DSI), Debtor Days (DSO), Days Payable (DPO), Cash Conversion Cycle (CCC), Order Book.
    """
    fetch = fetch_from_api_with_meta(ticker)
    if not fetch.data:
        tried_preview = "\n".join(fetch.tried_urls[:6])
        more = "" if len(fetch.tried_urls) <= 6 else f"\n...(+{len(fetch.tried_urls) - 6} more)"
        return (
            "Error: Could not fetch data from the API server.\n"
            f"Reason: {fetch.error}\n"
            "Tried URLs:\n"
            f"{tried_preview}{more}"
        )

    # Use the symbol variant that actually exists (important when user passes unsuffixed tickers)
    resolved_symbol = (ticker or "").strip().upper()
    if fetch.used_url and "/server/company/" in fetch.used_url:
        resolved_symbol = fetch.used_url.rsplit("/", 1)[-1].strip().upper() or resolved_symbol

    company, company_err, company_url = _best_effort_get_latest(f"/server/company/{resolved_symbol}")
    pnl, pnl_err, pnl_url = _best_effort_get_latest(f"/server/company/pnl/{resolved_symbol}")
    bs, bs_err, bs_url = _best_effort_get_latest(f"/server/company/balancesheet/{resolved_symbol}")

    # MAP DATA (best-effort based on common field names)
    revenue = _get_number(company, 'revenue', 'totalRevenue', default=_get_number(pnl, 'revenue', 'totalRevenue', default=0.0))
    cogs = _get_number(
        pnl,
        'costOfGoodsSold',
        'costOfRevenue',
        'cogs',
        'costAndExpenses',
        default=0.0,
    )
    inventory = _get_number(bs, 'inventory', 'inventories', default=0.0)
    receivables = _get_number(bs, 'netReceivables', 'accountsReceivable', 'receivables', default=0.0)
    payables = _get_number(bs, 'accountPayables', 'accountsPayable', 'payables', default=0.0)

    # Order book is not available in the current API contract
    order_book_note = "N/A (not provided by API)"

    # Basic validations
    if cogs == 0 and revenue == 0:
        return "Error: Revenue and COGS are zero. Cannot calculate metrics."

    # Use cogs for inventory turnover-related metrics; if cogs is zero but revenue exists, prefer revenue-based approximations
    denom_for_dsi = cogs if cogs else max(revenue, 1e-9)
    denom_for_dso = revenue if revenue else max(cogs, 1e-9)
    denom_for_dpo = cogs if cogs else max(revenue, 1e-9)

    dsi = (inventory / denom_for_dsi) * 365
    dso = (receivables / denom_for_dso) * 365
    dpo = (payables / denom_for_dpo) * 365
    ccc = dsi + dso - dpo

    status = '✅ Efficient' if ccc < 45 else '⚠️ Needs Improvement'

    source_line = fetch.used_url or company_url

    warnings: list[str] = []
    if not company:
        warnings.append(f"- Company overview missing ({_fmt_str(company_err)})")
    if not pnl:
        warnings.append(f"- P&L missing ({_fmt_str(pnl_err)})")
    if not bs:
        warnings.append(f"- Balance sheet missing ({_fmt_str(bs_err)})")
    if pnl and cogs == 0:
        warnings.append("- P&L fetched but COGS key not found (mapping mismatch)")
    if bs and inventory == 0 and receivables == 0 and payables == 0:
        warnings.append("- Balance sheet fetched but inventory/AR/AP keys not found (mapping mismatch)")

    currency = _first_present(company, ['reportedCurrency', 'currency']) or 'INR'
    money_prefix = '₹' if str(currency).upper() == 'INR' else '$'

    report = (
        f"FINANCIAL REPORT FOR: {resolved_symbol} (Source: {source_line})\n"
        "=============================================================\n"
        f"Currency: {currency}\n"
        f"Revenue: {money_prefix}{revenue:,.2f}\n"
        f"Inventory: {money_prefix}{inventory:,.2f}\n"
        f"Order Book: {order_book_note}\n\n"
        + ("WARNINGS:\n" + "\n".join(warnings) + "\n\n" if warnings else "")
        + "EFFICIENCY METRICS:\n"
        f"- Inventory Days (DSI): {dsi:.1f} days\n"
        f"- Debtor Days (DSO):    {dso:.1f} days\n"
        f"- Days Payable (DPO):   {dpo:.1f} days\n"
        f"- Cash Conversion Cycle: {ccc:.1f} days ({status})\n"
    )

    return report


@tool
def analyze_business_health_custom(ticker: str) -> str:
    """Tool wrapper for agent use. Returns the same report as `analyze_business_health`.
    """
    return analyze_business_health(ticker)


@tool
def analyze_company_snapshot_custom(ticker: str, calendar_year: int = 0, max_items: int = 5) -> str:
    """Fetch a broad company snapshot and return a readable report.

    Notes:
    - This is best-effort: if an endpoint doesn't exist or is slow, that section shows as N/A.
    - Order book is not included (assume not available).
    """
    ticker_raw = (ticker or "").strip()
    if not ticker_raw:
        return "Error: ticker is required (e.g., RELIANCE.NS)."

    try:
        max_items = int(max_items)
    except (TypeError, ValueError):
        max_items = 5
    max_items = max(1, min(max_items, 20))

    # Resolve symbol variant that exists
    exists = fetch_from_api_with_meta(ticker_raw)
    if not exists.data:
        tried_preview = "\n".join(exists.tried_urls[:6])
        more = "" if len(exists.tried_urls) <= 6 else f"\n...(+{len(exists.tried_urls) - 6} more)"
        return (
            "Error: Could not fetch data from the API server.\n"
            f"Reason: {exists.error}\n"
            "Tried URLs:\n"
            f"{tried_preview}{more}"
        )

    symbol = ticker_raw.upper()
    params_year = {"calendarYear": str(calendar_year)} if calendar_year else None

    company, company_err, company_url = _best_effort_get_latest(f"/server/company/{symbol}")
    pnl, pnl_err, pnl_url = _best_effort_get_latest(f"/server/company/pnl/{symbol}", params=params_year)
    bs, bs_err, bs_url = _best_effort_get_latest(f"/server/company/balancesheet/{symbol}", params=params_year)
    # Docs: /server/company/cfs/{company}
    cfs, cfs_err, cfs_url = _best_effort_get_latest(f"/server/company/cfs/{symbol}", params=params_year)

    quote, quote_err, quote_url = _best_effort_get_any(
        [
            f"/server/company/quote/{symbol}",
            f"/server/company/market/quote/{symbol}",
            f"/server/company/quotes/{symbol}",
        ]
    )

    ratios, ratios_err, ratios_url = _best_effort_get_any(
        [
            f"/server/company/ratios/{symbol}",
            f"/server/company/financialratios/{symbol}",
            f"/server/company/metrics/{symbol}",
        ],
        params=params_year,
    )

    links, links_err, links_url = _best_effort_get_any(
        [
            f"/server/company/links/{symbol}",
            f"/server/company/documents/{symbol}",
        ]
    )

    news, news_err, news_url = _best_effort_get_any(
        [
            # Docs: /server/news/{company}
            f"/server/news/{symbol}",
            f"/server/company/news/{symbol}",
        ]
    )

    # Docs sector comparison is keyed by sector name, not symbol.
    sector, sector_err, sector_url = None, "N/A (sector comparison requires sector name)", None

    rolling_options, ro_err, ro_url = _best_effort_get_any(
        [
            f"/server/company/options/rolling/{symbol}",
            f"/server/company/options/{symbol}",
        ]
    )

    option_chain, oc_err, oc_url = _best_effort_get_any(
        [
            f"/server/company/optionchain/{symbol}",
            f"/server/company/option-chain/{symbol}",
        ]
    )

    # --- Derive working capital metrics (still useful even with broader snapshot) ---
    revenue = _get_number(company, 'revenue', 'totalRevenue', default=_get_number(pnl, 'revenue', 'totalRevenue', default=0.0))
    cogs = _get_number(pnl, 'costOfGoodsSold', 'costOfRevenue', 'cogs', 'costAndExpenses', default=0.0)
    inventory = _get_number(bs, 'inventory', 'inventories', default=0.0)
    receivables = _get_number(bs, 'netReceivables', 'accountsReceivable', 'receivables', default=0.0)
    payables = _get_number(bs, 'accountPayables', 'accountsPayable', 'payables', default=0.0)

    denom_for_dsi = cogs if cogs else max(revenue, 1e-9)
    denom_for_dso = revenue if revenue else max(cogs, 1e-9)
    denom_for_dpo = cogs if cogs else max(revenue, 1e-9)

    dsi = (inventory / denom_for_dsi) * 365 if denom_for_dsi else 0.0
    dso = (receivables / denom_for_dso) * 365 if denom_for_dso else 0.0
    dpo = (payables / denom_for_dpo) * 365 if denom_for_dpo else 0.0
    ccc = dsi + dso - dpo

    # --- Format report ---
    lines: list[str] = []
    lines.append(f"COMPANY SNAPSHOT: {symbol}")
    lines.append("=" * 60)
    lines.append(f"Base URL: {BASE_URL}")
    if calendar_year:
        lines.append(f"Calendar Year (requested): {calendar_year}")
    lines.append("")

    # Overview
    lines.append("COMPANY OVERVIEW")
    lines.append("----------------")
    lines.append(f"Symbol: {_fmt_str(_first_present(company, ['symbol', 'ticker', 'code']))}")
    lines.append(f"Date: {_fmt_str(_first_present(company, ['date', 'reportedDate', 'asOfDate']))}")
    lines.append(f"Calendar Year: {_fmt_str(_first_present(company, ['calendarYear', 'year']))}")
    lines.append(f"Period: {_fmt_str(_first_present(company, ['period', 'quarter', 'fiscalPeriod']))}")
    lines.append(f"Currency: {_fmt_str(_first_present(company, ['reportedCurrency', 'currency']))}")
    currency = _first_present(company, ['reportedCurrency', 'currency']) or 'INR'
    money_prefix = '₹' if str(currency).upper() == 'INR' else '$'
    lines.append(f"Revenue: {_fmt_num(_first_present(company, ['revenue', 'totalRevenue']), prefix=money_prefix)}")
    lines.append(f"Net Income: {_fmt_num(_first_present(company, ['netIncome']), prefix=money_prefix)}")
    lines.append(f"EPS: {_fmt_num(_first_present(company, ['eps', 'epsDiluted', 'epsBasic']))}")
    lines.append(f"Market Cap: {_fmt_num(_first_present(company, ['marketCap', 'marketCapitalization', 'marketCapitalization']), prefix=money_prefix)}")
    lines.append("")

    # Efficiency (requested earlier)
    lines.append("WORKING CAPITAL METRICS")
    lines.append("----------------------")
    lines.append(f"Inventory Days (DSI): {dsi:.1f} days")
    lines.append(f"Debtor Days (DSO):   {dso:.1f} days")
    lines.append(f"Days Payable (DPO):  {dpo:.1f} days")
    lines.append(f"CCC:                {ccc:.1f} days")
    lines.append("Order Book: N/A (not provided)")
    lines.append("")

    # Quote / Market Depth
    lines.append("MARKET QUOTE (if available)")
    lines.append("---------------------------")
    if isinstance(quote, dict):
        ltp = _first_present(quote, ['ltp', 'lastTradedPrice', 'lastPrice', 'last'])
        open_p = _first_present(quote, ['open', 'openPrice'])
        high_p = _first_present(quote, ['high', 'highPrice'])
        low_p = _first_present(quote, ['low', 'lowPrice'])
        close_p = _first_present(quote, ['close', 'closePrice', 'previousClose'])
        avg_p = _first_present(quote, ['averagePrice', 'vwap'])
        last_qty = _first_present(quote, ['lastTradedQuantity', 'lastQty'])
        last_time = _first_present(quote, ['lastTradeTime', 'timestamp', 'time'])
        volume = _first_present(quote, ['volume', 'totalTradedVolume'])
        net_chg = _first_present(quote, ['netChange', 'change', 'changePercent'])
        lc = _first_present(quote, ['lowerCircuitLimit', 'lowerCircuit'])
        uc = _first_present(quote, ['upperCircuitLimit', 'upperCircuit'])
        buy_qty = _first_present(quote, ['buyQuantity', 'totalBuyQuantity', 'totalPendingBuyQuantity'])
        sell_qty = _first_present(quote, ['sellQuantity', 'totalSellQuantity', 'totalPendingSellQuantity'])

        lines.append(f"LTP: {_fmt_num(ltp)}")
        lines.append(f"Open/High/Low/Close: {_fmt_num(open_p)}/{_fmt_num(high_p)}/{_fmt_num(low_p)}/{_fmt_num(close_p)}")
        lines.append(f"Average (VWAP): {_fmt_num(avg_p)}")
        lines.append(f"Last Traded Qty: {_fmt_int(last_qty)}")
        lines.append(f"Last Trade Time: {_fmt_str(last_time)}")
        lines.append(f"Volume: {_fmt_int(volume)}")
        lines.append(f"Net Change: {_fmt_str(net_chg)}")
        lines.append(f"Lower/Upper Circuit: {_fmt_num(lc)}/{_fmt_num(uc)}")
        lines.append(f"Buy Qty / Sell Qty: {_fmt_int(buy_qty)} / {_fmt_int(sell_qty)}")

        depth = _first_present(quote, ['marketDepth', 'depth', 'orderBook'])
        bids = None
        asks = None
        if isinstance(depth, dict):
            bids = depth.get('bids') or depth.get('buy')
            asks = depth.get('asks') or depth.get('sell')
        if bids is not None or asks is not None:
            lines.append("")
            lines.append("Market Depth (top levels):")
            for side_name, side in (("Bids", bids), ("Asks", asks)):
                side_list = [x for x in _as_list(side) if isinstance(x, dict)]
                if not side_list:
                    continue
                lines.append(f"- {side_name}:")
                for lvl in side_list[:max_items]:
                    qty = _first_present(lvl, ['quantity', 'qty'])
                    orders = _first_present(lvl, ['orders', 'orderCount', 'noOfOrders'])
                    price = _first_present(lvl, ['price', 'rate'])
                    lines.append(f"  qty={_fmt_int(qty)} orders={_fmt_int(orders)} price={_fmt_num(price)}")
    else:
        lines.append(f"Not available. {_fmt_str(quote_err)}")
    lines.append("")

    # Rolling Options
    lines.append("ROLLING OPTIONS (if available)")
    lines.append("------------------------------")
    ro_list = [x for x in _as_list(rolling_options) if isinstance(x, dict)]
    if ro_list:
        for row in ro_list[:max_items]:
            strike = _first_present(row, ['strikePrice', 'strike'])
            o = _first_present(row, ['open', 'openPrice'])
            h = _first_present(row, ['high', 'highPrice'])
            l = _first_present(row, ['low', 'lowPrice'])
            c = _first_present(row, ['close', 'closePrice', 'lastPrice'])
            iv = _first_present(row, ['iv', 'impliedVolatility'])
            vol = _first_present(row, ['volume'])
            oi = _first_present(row, ['openInterest', 'oi'])
            spot = _first_present(row, ['spotPrice', 'underlyingPrice'])
            ts = _first_present(row, ['timestamp', 'time', 'epoch'])
            lines.append(
                f"Strike={_fmt_num(strike)} O/H/L/C={_fmt_num(o)}/{_fmt_num(h)}/{_fmt_num(l)}/{_fmt_num(c)} IV={_fmt_num(iv)} Vol={_fmt_int(vol)} OI={_fmt_int(oi)} Spot={_fmt_num(spot)} T={_fmt_str(ts)}"
            )
    else:
        lines.append(f"Not available. {_fmt_str(ro_err)}")
    lines.append("")

    # Option Chain
    lines.append("OPTION CHAIN (if available)")
    lines.append("---------------------------")
    if isinstance(option_chain, dict):
        underlying = _first_present(option_chain, ['underlyingLastPrice', 'underlyingPrice', 'spotPrice', 'lastPrice'])
        expiries = _as_list(_first_present(option_chain, ['expiries', 'expiryList', 'expiryDates']))
        lines.append(f"Underlying Last Price: {_fmt_num(underlying)}")
        if expiries:
            lines.append(f"Expiry count: {len(expiries)}")
            lines.append(f"First expiries: {', '.join([_fmt_str(x) for x in expiries[:min(5, len(expiries))]])}")

        strikes = _as_list(_first_present(option_chain, ['strikes', 'data', 'records']))
        strike_rows = [x for x in strikes if isinstance(x, dict)]
        if strike_rows:
            lines.append("Sample strikes:")
            for srow in strike_rows[:max_items]:
                sp = _first_present(srow, ['strikePrice', 'strike'])
                call = srow.get('call') or srow.get('CE') or srow.get('ce')
                put = srow.get('put') or srow.get('PE') or srow.get('pe')

                def fmt_leg(leg: Any) -> str:
                    if not isinstance(leg, dict):
                        return "N/A"
                    ltp = _first_present(leg, ['lastTradedPrice', 'ltp', 'lastPrice'])
                    oi = _first_present(leg, ['openInterest', 'oi'])
                    iv = _first_present(leg, ['impliedVolatility', 'iv'])
                    delta = _first_present(leg, ['delta'])
                    theta = _first_present(leg, ['theta'])
                    gamma = _first_present(leg, ['gamma'])
                    vega = _first_present(leg, ['vega'])
                    vol = _first_present(leg, ['volume'])
                    return (
                        f"LTP={_fmt_num(ltp)} OI={_fmt_int(oi)} IV={_fmt_num(iv)} Δ={_fmt_num(delta)} Θ={_fmt_num(theta)} Γ={_fmt_num(gamma)} V={_fmt_num(vega)} Vol={_fmt_int(vol)}"
                    )

                lines.append(f"- Strike { _fmt_num(sp) }: CALL[{fmt_leg(call)}] PUT[{fmt_leg(put)}]")
    else:
        lines.append(f"Not available. {_fmt_str(oc_err)}")
    lines.append("")

    # Financial statements
    lines.append("FINANCIAL STATEMENTS (latest or requested year)")
    lines.append("----------------------------------------------")
    lines.append(f"P&L source: {_fmt_str(pnl_url)}" + ("" if pnl_err is None else f" (note: {_fmt_str(pnl_err)})"))
    lines.append(f"Balance Sheet source: {_fmt_str(bs_url)}" + ("" if bs_err is None else f" (note: {_fmt_str(bs_err)})"))
    lines.append(f"Cash Flow source: {_fmt_str(cfs_url)}" + ("" if cfs_err is None else f" (note: {_fmt_str(cfs_err)})"))

    lines.append(f"Total Revenue: {_fmt_num(_first_present(pnl, ['revenue', 'totalRevenue']), prefix=money_prefix)}")
    lines.append(f"COGS: {_fmt_num(_first_present(pnl, ['costOfGoodsSold', 'costOfRevenue', 'cogs']), prefix=money_prefix)}")
    lines.append(f"Gross Profit: {_fmt_num(_first_present(pnl, ['grossProfit']), prefix=money_prefix)}")
    lines.append(f"Operating Income: {_fmt_num(_first_present(pnl, ['operatingIncome']), prefix=money_prefix)}")
    lines.append(f"EBITDA: {_fmt_num(_first_present(pnl, ['ebitda']), prefix=money_prefix)}")
    lines.append(f"Net Income: {_fmt_num(_first_present(pnl, ['netIncome']), prefix=money_prefix)}")

    lines.append(f"Total Assets: {_fmt_num(_first_present(bs, ['totalAssets']), prefix=money_prefix)}")
    lines.append(f"Total Liabilities: {_fmt_num(_first_present(bs, ['totalLiabilities']), prefix=money_prefix)}")
    lines.append(f"Inventory: {_fmt_num(_first_present(bs, ['inventory', 'inventories']), prefix=money_prefix)}")
    lines.append(f"Cash & Equivalents: {_fmt_num(_first_present(bs, ['cashAndCashEquivalents', 'cashAndCashEquivalentsAtCarryingValue', 'cashAndCashEquivalents']), prefix=money_prefix)}")

    lines.append(f"Operating Cash Flow: {_fmt_num(_first_present(cfs, ['operatingCashFlow', 'netCashProvidedByOperatingActivities']), prefix=money_prefix)}")
    lines.append(f"Capital Expenditure: {_fmt_num(_first_present(cfs, ['capitalExpenditure', 'capex']), prefix=money_prefix)}")
    lines.append(f"Free Cash Flow: {_fmt_num(_first_present(cfs, ['freeCashFlow']), prefix=money_prefix)}")
    lines.append("")

    # Ratios
    lines.append("FINANCIAL RATIOS (if available)")
    lines.append("-------------------------------")
    ratios_latest = _pick_latest(ratios)
    ratios_dict = ratios_latest if isinstance(ratios_latest, dict) else (ratios if isinstance(ratios, dict) else {})
    if ratios_dict:
        lines.append(f"PE: {_fmt_num(_first_present(ratios_dict, ['pe', 'peRatio', 'priceEarningsRatio']))}")
        lines.append(f"PB: {_fmt_num(_first_present(ratios_dict, ['pb', 'pbRatio', 'priceToBookRatio']))}")
        lines.append(f"ROA: {_fmt_num(_first_present(ratios_dict, ['roa', 'returnOnAssets']))}")
        lines.append(f"ROE: {_fmt_num(_first_present(ratios_dict, ['roe', 'returnOnEquity']))}")
        lines.append(f"Current Ratio: {_fmt_num(_first_present(ratios_dict, ['currentRatio']))}")
        lines.append(f"Debt/Equity: {_fmt_num(_first_present(ratios_dict, ['debtToEquity', 'debtEquityRatio']))}")
        lines.append(f"Interest Coverage: {_fmt_num(_first_present(ratios_dict, ['interestCoverage']))}")
        lines.append(f"Inventory Turnover: {_fmt_num(_first_present(ratios_dict, ['inventoryTurnover']))}")
        lines.append(f"Receivables Turnover: {_fmt_num(_first_present(ratios_dict, ['receivablesTurnover']))}")
    else:
        lines.append(f"Not available. {_fmt_str(ratios_err)}")
    lines.append("")

    # Links
    lines.append("DOCUMENT LINKS (if available)")
    lines.append("-----------------------------")
    link_items = []
    if isinstance(links, dict):
        # could be {'links': [...]} or direct dict of URLs
        candidate = links.get('links') if isinstance(links.get('links'), list) else None
        if candidate is not None:
            link_items = [x for x in candidate if isinstance(x, (str, dict))]
        else:
            link_items = [v for v in links.values() if isinstance(v, str)]
    elif isinstance(links, list):
        link_items = [x for x in links if isinstance(x, (str, dict))]
    if link_items:
        for item in link_items[:max_items]:
            if isinstance(item, str):
                lines.append(f"- {item}")
            elif isinstance(item, dict):
                title = _fmt_str(_first_present(item, ['title', 'name']), default="")
                url = _fmt_str(_first_present(item, ['url', 'link']))
                lines.append(f"- {title + ': ' if title else ''}{url}")
    else:
        lines.append(f"Not available. {_fmt_str(links_err)}")
    lines.append("")

    # News
    lines.append("COMPANY NEWS (if available)")
    lines.append("---------------------------")
    news_items = [x for x in _as_list(news) if isinstance(x, dict)]
    if news_items:
        for n in news_items[:max_items]:
            headline = _fmt_str(_first_present(n, ['headline', 'title']))
            date = _fmt_str(_first_present(n, ['date', 'publishedAt', 'time']))
            source = _fmt_str(_first_present(n, ['source', 'publisher']))
            url = _fmt_str(_first_present(n, ['url', 'link']))
            lines.append(f"- {headline} ({source}, {date})")
            if url != "N/A":
                lines.append(f"  {url}")
    else:
        lines.append(f"Not available. {_fmt_str(news_err)}")
    lines.append("")

    # Sector comparison
    lines.append("SECTOR COMPARISON (if available)")
    lines.append("-------------------------------")
    sector_items = [x for x in _as_list(sector) if isinstance(x, dict)]
    if sector_items:
        for row in sector_items[:max_items]:
            sym = _fmt_str(_first_present(row, ['symbol', 'ticker']))
            mc = _first_present(row, ['marketCap', 'marketCapitalization'])
            rev = _first_present(row, ['revenue', 'totalRevenue'])
            ni = _first_present(row, ['netIncome'])
            lines.append(f"- {sym} | MCap={_fmt_num(mc, prefix='$')} Rev={_fmt_num(rev, prefix='$')} NI={_fmt_num(ni, prefix='$')}")
    else:
        lines.append(f"Not available. {_fmt_str(sector_err)}")

    return "\n".join(lines)


if __name__ == '__main__':
    # Quick CLI runner for local testing
    import argparse

    parser = argparse.ArgumentParser(
        description='Fetch financial metrics for a ticker (for Indian stocks, use .NS/.BO e.g. RELIANCE.NS)'
    )
    parser.add_argument('ticker', nargs='?', default='TSLA')
    args = parser.parse_args()
    print('Fetching from:', BASE_URL)
    print(analyze_business_health(args.ticker))
