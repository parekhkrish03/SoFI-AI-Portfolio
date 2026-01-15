from langchain.tools import tool
from typing import Any, Dict, Optional

import requests

from custom_finance_tool import BASE_URL, _auth_headers, _get_number, fetch_from_api_with_meta, _unwrap_api_response, _pick_latest


def _compute_inventory_report(
    *,
    cogs: float,
    beginning_inventory: float,
    ending_inventory: float,
    source_note: Optional[str] = None,
) -> str:
    """Core inventory analysis used by both manual + API tools."""
    # ---- VALIDATION ----
    try:
        cogs = float(cogs)
        beginning_inventory = float(beginning_inventory)
        ending_inventory = float(ending_inventory)
    except (TypeError, ValueError):
        return "Error: Inputs must be numeric (cogs, beginning_inventory, ending_inventory)."

    if cogs <= 0:
        return "Error: COGS must be > 0 to calculate inventory metrics."
    if beginning_inventory < 0 or ending_inventory < 0:
        return "Error: Inventory values cannot be negative."

    days_in_year = 365.0

    # ---- CORE METRICS ----
    avg_inventory = (beginning_inventory + ending_inventory) / 2.0
    if avg_inventory == 0:
        return "Error: Average inventory is zero. Cannot calculate turnover/DSI."

    turnover_ratio = cogs / avg_inventory
    if turnover_ratio <= 0:
        return "Error: Turnover ratio is non-positive. Check inputs."

    dsi = days_in_year / turnover_ratio
    daily_cogs = cogs / days_in_year
    ending_cover_days = (ending_inventory / daily_cogs) if daily_cogs > 0 else float('inf')
    avg_cover_days = (avg_inventory / daily_cogs) if daily_cogs > 0 else float('inf')

    inventory_change = ending_inventory - beginning_inventory
    inventory_change_pct = (inventory_change / beginning_inventory * 100.0) if beginning_inventory else None

    # ---- INTERPRETATION ----
    if dsi > 120:
        health = "RED FLAG"
        headline = "Inventory is sitting too long; risk of obsolescence and cash tied up."
        actions = "Consider reducing purchase orders, discounting slow movers, and tightening demand forecasting."
    elif dsi < 15:
        health = "WARNING"
        headline = "Inventory is moving extremely fast; risk of stockouts and lost sales."
        actions = "Consider raising safety stock, shortening replenishment cycles, and improving supplier lead time reliability."
    else:
        health = "HEALTHY"
        headline = "Inventory turnover looks balanced."
        actions = "Maintain current replenishment policy; monitor trend and seasonality."

    trend_note = ""
    if inventory_change_pct is None:
        if beginning_inventory == 0 and ending_inventory > 0:
            trend_note = "Inventory increased from 0; confirm this is an intentional build."
    else:
        if inventory_change_pct > 25:
            trend_note = f"Inventory grew {inventory_change_pct:.1f}% over the period; check for demand slowdown or overbuying."
        elif inventory_change_pct < -25:
            trend_note = f"Inventory shrank {abs(inventory_change_pct):.1f}% over the period; check for under-ordering or supply constraints."

    lines = [
        "INVENTORY ANALYSIS",
        "------------------",
        f"Inputs: COGS={cogs:,.2f}, Begin Inv={beginning_inventory:,.2f}, End Inv={ending_inventory:,.2f}",
    ]
    if source_note:
        lines.append(f"Source: {source_note}")

    lines.extend([
        "",
        "Key Metrics:",
        f"- Average Inventory: {avg_inventory:,.2f}",
        f"- Turnover Ratio: {turnover_ratio:.2f}x/year",
        f"- Inventory Days (DSI): {dsi:.1f} days",
        f"- Daily COGS (avg): {daily_cogs:,.2f} per day",
        f"- Ending Inventory Coverage: {ending_cover_days:.1f} days of COGS",
        f"- Average Inventory Coverage: {avg_cover_days:.1f} days of COGS",
        "",
        f"Assessment: {health}",
        f"- {headline}",
    ])
    if trend_note:
        lines.append(f"- Trend: {trend_note}")
    lines.append(f"- Suggested next step: {actions}")

    return "\n".join(lines)

# This is the "A TOOL" box from your diagram
@tool
def analyze_inventory_levels(
    cogs: float, 
    beginning_inventory: float, 
    ending_inventory: float
) -> str:
    """
    Calculates inventory health metrics like Turnover Ratio and Days Sales of Inventory (DSI).
    
    Use this tool when the user asks about:
    - Inventory efficiency
    - How fast products are selling
    - Risk of dead stock or obsolescence
    
    Inputs:
    - cogs: Cost of Goods Sold (Annual).
    - beginning_inventory: Inventory value at start of year.
    - ending_inventory: Inventory value at end of year.
    """
    
    return _compute_inventory_report(
        cogs=cogs,
        beginning_inventory=beginning_inventory,
        ending_inventory=ending_inventory,
        source_note="Manual inputs",
    )


@tool
def analyze_inventory_levels_from_api(ticker: str) -> str:
    """Fetches COGS/inventory from the same API as `custom_finance_tool.py` and computes inventory metrics.

    Notes:
    - If the API only provides a single inventory value, it is used for both beginning and ending inventory.
    - Update key names below once you confirm the API JSON schema.
    """
    fetch = fetch_from_api_with_meta(ticker)
    if not fetch.data:
        tried_preview = "\n".join(fetch.tried_urls[:6])
        more = "" if len(fetch.tried_urls) <= 6 else f"\n...(+{len(fetch.tried_urls) - 6} more)"
        return (
            f"Error: Could not fetch data for {ticker} from {BASE_URL}.\n"
            f"Reason: {fetch.error}\n"
            "Tried URLs:\n"
            f"{tried_preview}{more}"
        )

    headers = _auth_headers()
    if not headers:
        return "Error: Missing API key. Set AC_API_KEY (used as x-api-key header) before calling the API."

    symbol = (ticker or "").strip().upper()
    pnl_url = f"{BASE_URL}/server/company/pnl/{symbol}"
    bs_url = f"{BASE_URL}/server/company/balancesheet/{symbol}"

    def get_latest(url: str):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            return _pick_latest(_unwrap_api_response(r.json())) or {}
        except requests.exceptions.RequestException:
            return {}

    pnl = get_latest(pnl_url)
    bs = get_latest(bs_url)

    cogs = _get_number(pnl, 'costOfGoodsSold', 'costOfRevenue', 'cogs', 'costAndExpenses', default=0.0)

    # Many APIs only provide a single inventory number. Use it for begin/end.
    inv_single = _get_number(bs, 'inventory', 'inventories', default=0.0)
    inv_begin = inv_single
    inv_end = inv_single

    note = f"API: {pnl_url} + {bs_url}"

    return _compute_inventory_report(
        cogs=cogs,
        beginning_inventory=inv_begin,
        ending_inventory=inv_end,
        source_note=note,
    )