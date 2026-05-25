"""
Profit Quality Analysis Tool — Module 1 of the SoFi Forensic Analysis Toolkit

This module exposes ONE LangChain @tool: run_profit_quality_analysis(ticker).
The tool fetches 10 years of live financial data from the portfolio analyser's
financial database API and runs seven forensic sub-checks on profit quality,
accrual quality, and cash conversion. Returns a composite Profit Quality Score
(A–D grade) plus detailed per-check breakdowns.

The tool is designed to be called by an orchestrating LangChain agent that
will coordinate this module with others (revenue quality, debt leverage,
working capital, etc.) to produce a complete forensic analysis report.

Usage:
    from profit_quality_tool import run_profit_quality_analysis
    result_json = run_profit_quality_analysis.invoke({"ticker": "RELIANCE"})
    import json
    result = json.loads(result_json)
    print(result["scorecard"]["grade"])

All monetary values in ₹ Crores (Indian standard).
"""

import os
import json
import statistics
from typing import Optional, Dict, List, Any
from datetime import datetime

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

STOCK_API_BASE_URL = os.environ.get("STOCK_API_BASE_URL", "").rstrip("/")
STOCK_API_KEY = os.environ.get("STOCK_API_KEY", "")
API_TIMEOUT = float(os.environ.get("API_TIMEOUT", "10"))
DEFAULT_RISK_FREE_RATE = float(os.environ.get("DEFAULT_RISK_FREE_RATE", "0.072"))

# Field name aliases (map API field names to canonical names)
ALIASES = {
    "revenue": "net_sales",
    "sales": "net_sales",
    "total_revenue": "net_sales",
    "ocf": "cfo",
    "operating_cf": "cfo",
    "d_and_a": "depreciation",
    "da": "depreciation",
    "capital_expenditure": "capex",
    "interest_earned": "interest_income",
    "net_debt_change": "net_borrowings",
}

# Weights for composite score (sum = 100)
SCORE_WEIGHTS = {
    "pat_vs_cfo": 0.25,
    "cfo_ebitda": 0.20,
    "accrual": 0.20,
    "ccs": 0.10,
    "dep_volatility": 0.10,
    "cash_vs_rfr": 0.05,
    "fcfe": 0.10,
}

# =============================================================================
# INPUT SCHEMA
# =============================================================================

class TickerInput(BaseModel):
    """Input schema for profit quality analysis tool."""
    ticker: str = Field(
        description="Indian stock ticker (NSE/BSE symbol). "
                    "Examples: RELIANCE, INFY, HDFCBANK, TCS, WIPRO"
    )


# =============================================================================
# HELPER FUNCTIONS — DATA FETCHING & NORMALIZATION
# =============================================================================

def _get_headers() -> Dict[str, str]:
    """Return HTTP headers with API authentication."""
    return {
        "x-api-key": STOCK_API_KEY,
        "Content-Type": "application/json"
    }


def _fetch_raw(ticker: str, years: int = 10) -> Optional[Dict[str, Any]]:
    """
    Fetch raw JSON from API.
    
    Returns response dict or None on error.
    """
    if not STOCK_API_BASE_URL or not STOCK_API_KEY:
        raise ValueError("CONFIGURATION_ERROR: Missing STOCK_API_BASE_URL or STOCK_API_KEY")
    
    # Add .NS suffix if not present (NSE listing)
    if not ticker.endswith((".NS", ".BO")):
        ticker = f"{ticker}.NS"
    
    url = f"{STOCK_API_BASE_URL}/server/company/{ticker}"
    
    try:
        response = requests.get(
            url,
            headers=_get_headers(),
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 404:
            return None  # Ticker not found
        
        response.raise_for_status()
        return response.json()
    
    except requests.RequestException:
        return None  # API error, rate limit, timeout, etc


def _normalize_field_name(field: str) -> str:
    """Map API field name to canonical name using ALIASES dict."""
    return ALIASES.get(field.lower(), field.lower())


def _normalise_year_data(year_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single year's data object: remap field names and convert to float.
    
    Returns dict with canonical keys (net_sales, cfo, ebitda, etc.).
    """
    normalized = {}
    
    for key, value in year_obj.items():
        canonical_key = _normalize_field_name(key)
        try:
            normalized[canonical_key] = float(value) if value is not None else None
        except (ValueError, TypeError):
            normalized[canonical_key] = None
    
    return normalized


def _get_financials(ticker: str, years: int = 10) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch and normalize financial data from API.
    
    Returns sorted list of year dicts (oldest first), or None on error.
    Each dict has keys: year, pat, cfo, ebitda, depreciation, net_sales, cash,
    interest_income, risk_free_rate, total_assets, total_liabilities, capex,
    net_borrowings.
    """
    raw = _fetch_raw(ticker, years)
    if not raw:
        return None
    
    # Extract years array from AC API response
    years_list = raw.get("data") or []
    if not isinstance(years_list, list) or len(years_list) == 0:
        return None
    
    # Map AC API field names to our canonical names; convert from INR to crores
    normalized = []
    for year_obj in years_list:
        normalized_year = {
            "year": year_obj.get("calendarYear"),
            "pat": _safe_float(year_obj.get("netIncome")) / 10000000 if year_obj.get("netIncome") else None,
            "cfo": _safe_float(year_obj.get("operatingCashFlow")) / 10000000 if year_obj.get("operatingCashFlow") else None,
            "ebitda": _safe_float(year_obj.get("ebitda")) / 10000000 if year_obj.get("ebitda") else None,
            "depreciation": _safe_float(year_obj.get("depreciationAndAmortization")) / 10000000 if year_obj.get("depreciationAndAmortization") else None,
            "net_sales": _safe_float(year_obj.get("revenue")) / 10000000 if year_obj.get("revenue") else None,
            "cash": _safe_float(year_obj.get("cashAndCashEquivalents")) / 10000000 if year_obj.get("cashAndCashEquivalents") else None,
            "interest_income": _safe_float(year_obj.get("interestIncome")) / 10000000 if year_obj.get("interestIncome") else None,
            "risk_free_rate": DEFAULT_RISK_FREE_RATE,
            "total_assets": _safe_float(year_obj.get("totalAssets")) / 10000000 if year_obj.get("totalAssets") else None,
            "total_liabilities": _safe_float(year_obj.get("totalLiabilities")) / 10000000 if year_obj.get("totalLiabilities") else None,
            "capex": abs(_safe_float(year_obj.get("netCashUsedForInvestingActivites")) / 10000000) if year_obj.get("netCashUsedForInvestingActivites") else None,
            "net_borrowings": _safe_float(year_obj.get("netChangeInCash")) / 10000000 if year_obj.get("netChangeInCash") else None,
        }
        normalized.append(normalized_year)
    
    # Sort by year (oldest first)
    normalized.sort(key=lambda x: x.get("year", 0))
    
    return normalized


def _safe_float(val: Any) -> Optional[float]:
    """Safely convert to float, return None if not possible."""
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _safe_divide(num: Optional[float], denom: Optional[float]) -> Optional[float]:
    """Safely divide, return None if denom is zero or None."""
    if num is None or denom is None or denom == 0:
        return None
    return num / denom


def _flag3(value: Optional[float], pass_threshold: float, warn_threshold: float, 
           higher_is_better: bool = True) -> tuple:
    """
    Classify value into 3-tier flag system: PASS / WARN / FAIL.
    
    Args:
        value: Metric value (or None)
        pass_threshold: Threshold for PASS
        warn_threshold: Threshold for WARN (between PASS and FAIL)
        higher_is_better: If True, higher value = better; if False, lower = better
    
    Returns:
        (flag_str, numeric_score) where score is 100 (PASS), 50 (WARN), 0 (FAIL), -1 (N/A)
    """
    if value is None:
        return ("⚪ N/A", -1)
    
    if higher_is_better:
        if value >= pass_threshold:
            return ("✅ PASS", 100)
        elif value >= warn_threshold:
            return ("⚠️ WARN", 50)
        else:
            return ("🚨 FAIL", 0)
    else:
        if value <= pass_threshold:
            return ("✅ PASS", 100)
        elif value <= warn_threshold:
            return ("⚠️ WARN", 50)
        else:
            return ("🚨 FAIL", 0)


def _cv(values: List[float]) -> Optional[float]:
    """
    Calculate coefficient of variation: stdev / |mean|.
    Return None if insufficient data or mean is zero.
    """
    valid = [v for v in values if v is not None and v != 0]
    if len(valid) < 2:
        return None
    
    mean = statistics.mean(valid)
    if mean == 0:
        return None
    
    stdev = statistics.stdev(valid)
    return stdev / abs(mean)


# =============================================================================
# FORENSIC CHECKS — Pure calculation functions
# =============================================================================

def _check_pat_vs_cfo(years_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check 1: PAT vs CFO Divergence (10 years + rolling 3 years)
    
    Formula: Divergence% = (ΣPAT − ΣCFO) / |ΣPAT| × 100
    
    Interpretation:
      PASS → divergence < 10 %
      WARN → 10 % ≤ divergence < 25 %
      FAIL → divergence ≥ 25 %
    """
    years_data = [y for y in years_data if y.get("pat") is not None and y.get("cfo") is not None]
    
    if len(years_data) == 0:
        return {
            "name": "PAT vs CFO Divergence (10Y + Rolling 3Y)",
            "value": None,
            "unit": "%",
            "flag": "⚪ N/A",
            "score": -1,
            "detail": "Insufficient data"
        }
    
    # 10-year cumulative
    total_pat = sum(_safe_float(y.get("pat")) or 0 for y in years_data)
    total_cfo = sum(_safe_float(y.get("cfo")) or 0 for y in years_data)
    
    if total_pat == 0:
        divergence = None
    else:
        divergence = abs((total_pat - total_cfo) / total_pat) * 100
    
    flag_str, score = _flag3(divergence, 10, 25, higher_is_better=False)
    
    # Rolling 3-year if we have enough data
    rolling_3y = []
    if len(years_data) >= 3:
        for i in range(len(years_data) - 2):
            window = years_data[i:i+3]
            pat_3y = sum(_safe_float(y.get("pat")) or 0 for y in window)
            cfo_3y = sum(_safe_float(y.get("cfo")) or 0 for y in window)
            if pat_3y > 0:
                div_3y = abs((pat_3y - cfo_3y) / pat_3y) * 100
                rolling_3y.append({
                    "year_end": window[-1].get("year"),
                    "divergence_pct": round(div_3y, 2)
                })
    
    return {
        "name": "PAT vs CFO Divergence (10Y + Rolling 3Y)",
        "value": round(divergence, 2) if divergence else None,
        "unit": "%",
        "flag": flag_str,
        "score": score,
        "detail": f"Cumulative PAT: {round(total_pat, 0)}, CFO: {round(total_cfo, 0)}",
        "rolling_3y": rolling_3y
    }


def _check_cfo_ebitda(years_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check 2: CFO / EBITDA Consistency
    
    Formula: Ratio_t = CFO_t / EBITDA_t
    
    EBITDA reconstructed as: PAT + Tax + Interest + D&A (if not provided)
    
    Interpretation:
      PASS → ratio ≥ 0.7
      WARN → 0.5 ≤ ratio < 0.7
      FAIL → ratio < 0.5
    """
    ratios = []
    
    for year_data in years_data:
        cfo = _safe_float(year_data.get("cfo"))
        ebitda = _safe_float(year_data.get("ebitda"))
        
        # If EBITDA not provided, estimate as PAT + D&A (simplified)
        if ebitda is None:
            pat = _safe_float(year_data.get("pat"))
            da = _safe_float(year_data.get("depreciation"))
            if pat is not None and da is not None:
                ebitda = pat + da
        
        ratio = _safe_divide(cfo, ebitda)
        if ratio is not None:
            ratios.append(ratio)
    
    if len(ratios) == 0:
        return {
            "name": "CFO / EBITDA Consistency",
            "value": None,
            "unit": "Ratio",
            "flag": "⚪ N/A",
            "score": -1,
            "detail": "Insufficient data"
        }
    
    avg_ratio = statistics.mean(ratios)
    flag_str, score = _flag3(avg_ratio, 0.7, 0.5, higher_is_better=True)
    
    return {
        "name": "CFO / EBITDA Consistency",
        "value": round(avg_ratio, 2),
        "unit": "Ratio",
        "flag": flag_str,
        "score": score,
        "detail": f"Average ratio across {len(ratios)} years",
        "yearly_ratios": [
            {"year": y.get("year"), "ratio": round(_safe_divide(_safe_float(y.get("cfo")), _safe_float(y.get("ebitda")) or _safe_float(y.get("pat")) or 1) or 0, 2)}
            for y in years_data
        ]
    }


def _check_accrual(years_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check 3: Balance-Sheet Accrual Ratio (Richardson et al., JAR 2005)
    
    Formula: 
      NOA_t = (Total Assets_t − Cash_t) − Total Liabilities_t
      Accrual Ratio_t = (NOA_t − NOA_t-1) / Avg(Total Assets) × 100
    
    Interpretation:
      PASS → avg accrual < 3 %
      WARN → 3 % ≤ avg < 7 %
      FAIL → avg ≥ 7 %
    """
    accrual_ratios = []
    
    for i in range(1, len(years_data)):
        curr = years_data[i]
        prev = years_data[i - 1]
        
        curr_assets = _safe_float(curr.get("total_assets"))
        curr_cash = _safe_float(curr.get("cash"))
        curr_liab = _safe_float(curr.get("total_liabilities"))
        
        prev_assets = _safe_float(prev.get("total_assets"))
        prev_cash = _safe_float(prev.get("cash"))
        prev_liab = _safe_float(prev.get("total_liabilities"))
        
        # Calculate NOA (Net Operating Assets)
        if curr_assets and curr_liab and curr_cash is not None:
            noa_curr = (curr_assets - curr_cash) - curr_liab
        else:
            noa_curr = None
        
        if prev_assets and prev_liab and prev_cash is not None:
            noa_prev = (prev_assets - prev_cash) - prev_liab
        else:
            noa_prev = None
        
        # Calculate accrual ratio
        if noa_curr is not None and noa_prev is not None and curr_assets is not None and prev_assets is not None:
            avg_assets = (curr_assets + prev_assets) / 2
            if avg_assets > 0:
                accrual_ratio = ((noa_curr - noa_prev) / avg_assets) * 100
                accrual_ratios.append(accrual_ratio)
    
    if len(accrual_ratios) == 0:
        return {
            "name": "Balance-Sheet Accrual Ratio",
            "value": None,
            "unit": "%",
            "flag": "⚪ N/A",
            "score": -1,
            "detail": "Insufficient data"
        }
    
    avg_accrual = statistics.mean(accrual_ratios)
    flag_str, score = _flag3(avg_accrual, 3, 7, higher_is_better=False)
    
    return {
        "name": "Balance-Sheet Accrual Ratio",
        "value": round(avg_accrual, 2),
        "unit": "%",
        "flag": flag_str,
        "score": score,
        "detail": f"Average accrual ratio across {len(accrual_ratios)} years"
    }


def _check_ccs(years_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check 4: Cash Conversion Score (CCS)
    
    Formula: CCS_t = CFO_t / PAT_t × 100
    
    Interpretation:
      PASS → avg CCS ≥ 70 %
      WARN → 50 % ≤ avg CCS < 70 %
      FAIL → avg CCS < 50 %
    """
    ccs_values = []
    
    for year_data in years_data:
        cfo = _safe_float(year_data.get("cfo"))
        pat = _safe_float(year_data.get("pat"))
        
        if cfo is not None and pat is not None and pat > 0:
            ccs = (cfo / pat) * 100
            ccs_values.append(ccs)
    
    if len(ccs_values) == 0:
        return {
            "name": "Cash Conversion Score (CCS)",
            "value": None,
            "unit": "%",
            "flag": "⚪ N/A",
            "score": -1,
            "detail": "Insufficient data"
        }
    
    avg_ccs = statistics.mean(ccs_values)
    flag_str, score = _flag3(avg_ccs, 70, 50, higher_is_better=True)
    
    return {
        "name": "Cash Conversion Score (CCS)",
        "value": round(avg_ccs, 2),
        "unit": "%",
        "flag": flag_str,
        "score": score,
        "detail": f"Average CCS across {len(ccs_values)} years (target ≥70%)"
    }


def _check_dep_volatility(years_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check 5: Depreciation Rate Volatility
    
    Formula: Dep_Rate_t% = Depreciation_t / Net_Sales_t × 100
             σ = stdev(Dep_Rate across years)
    
    Interpretation:
      STABLE → σ < 0.5 percentage points
      WATCH → 0.5 ≤ σ < 1.0
      VOLATILE → σ ≥ 1.0
    """
    dep_rates = []
    
    for year_data in years_data:
        dep = _safe_float(year_data.get("depreciation"))
        sales = _safe_float(year_data.get("net_sales"))
        
        if dep is not None and sales is not None and sales > 0:
            dep_rate = (dep / sales) * 100
            dep_rates.append(dep_rate)
    
    if len(dep_rates) < 2:
        return {
            "name": "Depreciation Rate Volatility",
            "value": None,
            "unit": "std dev (pct points)",
            "flag": "⚪ N/A",
            "score": -1,
            "detail": "Insufficient data"
        }
    
    stdev_dep = statistics.stdev(dep_rates)
    
    if stdev_dep < 0.5:
        flag_str, score = "🟢 STABLE", 100
    elif stdev_dep < 1.0:
        flag_str, score = "🟡 WATCH", 50
    else:
        flag_str, score = "🔴 VOLATILE", 0
    
    return {
        "name": "Depreciation Rate Volatility",
        "value": round(stdev_dep, 3),
        "unit": "std dev (pct points)",
        "flag": flag_str,
        "score": score,
        "detail": f"Standard deviation of dep% of sales"
    }


def _check_cash_vs_rfr(years_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check 6: Cash Yield vs 10Y G-Sec
    
    Formula: 
      Implied_Yield_t% = Interest_Income_t / Cash_t × 100
      Spread_t% = Implied_Yield_t − (G-Sec_Yield_t × 100)
    
    Interpretation:
      PASS → spread ≥ 0 %
      WARN → −1 % ≤ spread < 0 %
      BELOW RFR → spread < −1 %
    """
    spreads = []
    
    for year_data in years_data:
        interest = _safe_float(year_data.get("interest_income"))
        cash = _safe_float(year_data.get("cash"))
        rfr = _safe_float(year_data.get("risk_free_rate")) or DEFAULT_RISK_FREE_RATE
        
        if interest is not None and cash is not None and cash > 0:
            implied_yield_pct = (interest / cash) * 100
            rfr_pct = rfr * 100
            spread = implied_yield_pct - rfr_pct
            spreads.append(spread)
    
    if len(spreads) == 0:
        return {
            "name": "Cash Yield vs 10Y G-Sec",
            "value": None,
            "unit": "Spread (%)",
            "flag": "⚪ N/A",
            "score": -1,
            "detail": "Insufficient data"
        }
    
    avg_spread = statistics.mean(spreads)
    flag_str, score = _flag3(avg_spread, 0, -1, higher_is_better=True)
    
    return {
        "name": "Cash Yield vs 10Y G-Sec",
        "value": round(avg_spread, 2),
        "unit": "Spread (%)",
        "flag": flag_str,
        "score": score,
        "detail": f"Average spread of {len(spreads)} years (positive = better)"
    }


def _check_fcfe(years_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check 7: FCFE Generation & Lumpiness
    
    Formula: FCFE_t = CFO_t − Capex_t + Net_Borrowings_t
             CV = stdev(FCFE) / |mean(FCFE)| × 100
    
    Interpretation:
      HEALTHY → negative years 0–1 / 10
      WATCH → negative years 2–3 / 10
      CONCERN → negative years ≥ 4 / 10
    """
    fcfe_values = []
    negative_count = 0
    
    for year_data in years_data:
        cfo = _safe_float(year_data.get("cfo"))
        capex = _safe_float(year_data.get("capex"))
        net_borrow = _safe_float(year_data.get("net_borrowings"))
        
        if cfo is not None and capex is not None and net_borrow is not None:
            fcfe = cfo - capex + net_borrow
            fcfe_values.append(fcfe)
            if fcfe < 0:
                negative_count += 1
    
    if len(fcfe_values) == 0:
        return {
            "name": "FCFE Generation & Lumpiness",
            "value": None,
            "unit": "FCFE ₹Cr",
            "flag": "⚪ N/A",
            "score": -1,
            "detail": "Insufficient data"
        }
    
    # Classify based on negative years
    if negative_count <= 1:
        flag_str, score = "🟢 HEALTHY", 100
    elif negative_count <= 3:
        flag_str, score = "🟡 WATCH", 50
    else:
        flag_str, score = "🔴 CONCERN", 0
    
    avg_fcfe = statistics.mean(fcfe_values)
    
    return {
        "name": "FCFE Generation & Lumpiness",
        "value": round(avg_fcfe, 0),
        "unit": "FCFE ₹Cr (avg)",
        "flag": flag_str,
        "score": score,
        "detail": f"FCFE negative in {negative_count}/{len(fcfe_values)} years"
    }


# =============================================================================
# MAIN TOOL
# =============================================================================

@tool(args_schema=TickerInput)
def run_profit_quality_analysis(ticker: str) -> str:
    """
    Run comprehensive profit quality analysis on an Indian stock.
    
    Fetches 10 years of financial data from the portfolio analyser's API,
    runs seven forensic sub-checks, and returns a composite Profit Quality
    Score (A–D grade) with detailed breakdowns.
    
    Args:
        ticker: Indian stock symbol (NSE/BSE). Examples: RELIANCE, INFY, HDFCBANK
    
    Returns:
        JSON string with:
        - scorecard: profit_quality_score (0–100), grade (A–D), red_flag_count
        - checks: detailed results for each of 7 sub-checks
        - data_warnings: any data gaps or issues
    
    All monetary values in ₹ Crores.
    """
    
    # =========================================================================
    # ERROR HANDLING — Configuration
    # =========================================================================
    
    if not STOCK_API_BASE_URL or not STOCK_API_KEY:
        return json.dumps({
            "error": "CONFIGURATION_ERROR",
            "detail": "Missing STOCK_API_BASE_URL or STOCK_API_KEY in .env",
            "ticker": ticker
        }, indent=2, default=str)
    
    # =========================================================================
    # FETCH DATA
    # =========================================================================
    
    try:
        years_data = _get_financials(ticker, years=10)
    except Exception as e:
        return json.dumps({
            "error": "UNEXPECTED_ERROR",
            "detail": str(e),
            "ticker": ticker
        }, indent=2, default=str)
    
    # =========================================================================
    # ERROR HANDLING — Ticker/Data
    # =========================================================================
    
    if years_data is None:
        return json.dumps({
            "error": "TICKER_NOT_FOUND",
            "detail": f"No financial data found for ticker: {ticker}",
            "ticker": ticker
        }, indent=2, default=str)
    
    if len(years_data) == 0:
        return json.dumps({
            "error": "API_ERROR",
            "detail": f"API returned empty years array for {ticker}",
            "ticker": ticker
        }, indent=2, default=str)
    
    # =========================================================================
    # RUN CHECKS
    # =========================================================================
    
    check_results = {
        "pat_vs_cfo": _check_pat_vs_cfo(years_data),
        "cfo_ebitda": _check_cfo_ebitda(years_data),
        "accrual": _check_accrual(years_data),
        "ccs": _check_ccs(years_data),
        "dep_volatility": _check_dep_volatility(years_data),
        "cash_vs_rfr": _check_cash_vs_rfr(years_data),
        "fcfe": _check_fcfe(years_data),
    }
    
    # =========================================================================
    # COMPUTE COMPOSITE SCORE
    # =========================================================================
    
    component_scores = {}
    total_weighted_score = 0
    red_flag_count = 0
    
    for check_key, check_result in check_results.items():
        score = check_result.get("score", -1)
        weight = SCORE_WEIGHTS.get(check_key, 0)
        
        # Count red flags (score == 0)
        if score == 0:
            red_flag_count += 1
        
        # Accumulate weighted score (skip N/A scores)
        if score >= 0:
            component_scores[check_key] = {
                "raw_score": score,
                "weight": weight,
                "weighted_contribution": score * weight
            }
            total_weighted_score += score * weight
    
    # Determine grade
    profit_quality_score = round(total_weighted_score, 1)
    
    if profit_quality_score >= 80:
        grade = "A — HIGH QUALITY"
    elif profit_quality_score >= 60:
        grade = "B — ADEQUATE"
    elif profit_quality_score >= 40:
        grade = "C — BELOW PAR"
    else:
        grade = "D — POOR QUALITY"
    
    # =========================================================================
    # BUILD RESPONSE
    # =========================================================================
    
    analysis_date = datetime.now().strftime("%Y-%m-%d")
    year_range = f"{years_data[0].get('year')} – {years_data[-1].get('year')}"
    
    response = {
        "ticker": ticker.upper(),
        "analysis_date": analysis_date,
        "years_of_data": len(years_data),
        "year_range": year_range,
        
        "scorecard": {
            "profit_quality_score": profit_quality_score,
            "max_score": 100,
            "grade": grade,
            "red_flag_count": red_flag_count,
            "component_scores": component_scores,
        },
        
        "checks": check_results,
        
        "data_warnings": [],
        
        "module": "profit_quality",
        "toolkit": "SoFi Forensic Analysis | AI Portfolio Analyser"
    }
    
    return json.dumps(response, indent=2, default=str)


# =============================================================================
# STANDALONE TEST (optional)
# =============================================================================

if __name__ == "__main__":
    import sys
    
    ticker = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
    print(f"Testing with ticker: {ticker}\n")
    
    result = run_profit_quality_analysis.invoke({"ticker": ticker})
    print(result)
