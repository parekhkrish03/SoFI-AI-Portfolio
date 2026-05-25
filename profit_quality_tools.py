"""
Profit Quality & Accrual Analysis Tools for LangChain/LangGraph Agents

This module provides LangChain-compatible tools for forensic financial analysis
of Indian-listed stocks (NSE/BSE). Covers the Profit Quality & Accrual Analysis
cluster from the SoFi Forensic Analysis Checklist.

Tools:
  - cumulative_pat_vs_cfo:      10-year + rolling 3-year PAT vs CFO divergence
  - cfo_ebitda_consistency:     CFO/EBITDA ratio consistency check (>0.7)
  - accrual_profit_conversion:  Accrual ratio + Cash Conversion Score
  - depreciation_volatility:    Depreciation % of sales stability
  - cash_return_vs_riskfree:    Cash balance return vs 10Y risk-free rate
  - fcfe_lumpiness:             FCFE generation trend & lumpy cash flow detection

All monetary values in ₹ Crores (Indian standard).

Usage:
    from profit_quality_tools import cumulative_pat_vs_cfo
    result = cumulative_pat_vs_cfo.invoke({"ticker": "RELIANCE"})
"""

import os
import json
import statistics
from typing import Optional, List, Dict, Any

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

STOCK_API_BASE_URL = os.environ.get(
    "STOCK_API_BASE_URL",
    "https://stock-api.example.com"  # Replace with actual API
)
STOCK_API_KEY = os.environ.get("STOCK_API_KEY", "")
REQUEST_TIMEOUT = float(os.environ.get("STOCK_API_TIMEOUT", "10"))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_headers() -> Dict[str, str]:
    """Return HTTP headers with API authentication."""
    return {
        "Authorization": f"Bearer {STOCK_API_KEY}",
        "Content-Type": "application/json"
    }


def _fetch_financials(ticker: str, years: int = 10) -> Optional[Dict[str, Any]]:
    """
    Fetch annual financial data from the stock API.
    
    Args:
        ticker: NSE/BSE symbol (e.g., "RELIANCE", "INFY")
        years: Number of years to fetch (default 10)
    
    Returns:
        Dict with "years" array, or None on failure.
        
    Fields in each year object (all monetary in ₹ Crores):
        - year, pat, cfo, ebitda, depreciation, sales, cash, capex,
          interest_income, risk_free_rate, total_assets, total_liabilities,
          equity_raised, debt_repayment
    """
    url = f"{STOCK_API_BASE_URL}/financials/annual"
    params = {"ticker": ticker, "years": years}
    
    try:
        response = requests.get(
            url,
            params=params,
            headers=_get_headers(),
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching financials for {ticker}: {e}")
        return None


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float, return None if not possible."""
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Safely divide, return None if denominator is zero or None."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _coefficient_of_variation(values: List[float]) -> Optional[float]:
    """
    Calculate coefficient of variation (std dev / mean).
    Returns None if insufficient data or mean is zero.
    """
    if not values or len(values) < 2:
        return None
    
    valid_values = [v for v in values if v is not None and v != 0]
    if len(valid_values) < 2:
        return None
    
    mean = statistics.mean(valid_values)
    if mean == 0:
        return None
    
    stdev = statistics.stdev(valid_values)
    return stdev / abs(mean)


# =============================================================================
# INPUT SCHEMAS
# =============================================================================

class TickerInput(BaseModel):
    """Input schema for profit quality tools."""
    ticker: str = Field(
        description="Indian stock ticker symbol (NSE/BSE). "
                    "Examples: RELIANCE, INFY, HDFCBANK, TCS"
    )


# =============================================================================
# TOOLS
# =============================================================================

@tool(args_schema=TickerInput)
def cumulative_pat_vs_cfo(ticker: str) -> str:
    """
    Analyze 10-year cumulative PAT vs CFO divergence.
    
    Flags earnings quality issues: if cumulative PAT substantially exceeds
    cumulative CFO, indicates accruals/non-cash earnings.
    
    Args:
        ticker: Indian stock symbol (e.g., RELIANCE, INFY)
    
    Returns:
        JSON string with:
        - cumulative_10y: {pat_crores, cfo_crores, divergence_ratio, flag}
        - rolling_3y: [{year, cumulative_pat, cumulative_cfo, divergence}]
        - interpretation: Text explanation
    
    Monetary values in ₹ Crores.
    """
    data = _fetch_financials(ticker, years=10)
    if not data or "years" not in data:
        return json.dumps({"error": f"Failed to fetch data for {ticker}"}, indent=2)
    
    years_list = sorted(data["years"], key=lambda x: x.get("year", 0))
    
    # 10-year cumulative
    cumulative_pat = sum(_safe_float(y.get("pat")) or 0 for y in years_list)
    cumulative_cfo = sum(_safe_float(y.get("cfo")) or 0 for y in years_list)
    
    divergence_ratio = _safe_divide(cumulative_pat, cumulative_cfo)
    pat_cfo_flag = "⚠️ HIGH" if divergence_ratio and divergence_ratio > 1.2 else "✓ NORMAL"
    
    # Rolling 3-year analysis
    rolling_3y = []
    for i in range(len(years_list) - 2):
        period = years_list[i:i+3]
        cum_pat_3y = sum(_safe_float(y.get("pat")) or 0 for y in period)
        cum_cfo_3y = sum(_safe_float(y.get("cfo")) or 0 for y in period)
        div_3y = _safe_divide(cum_pat_3y, cum_cfo_3y)
        
        rolling_3y.append({
            "year_end": period[-1].get("year"),
            "cumulative_pat_3y": round(cum_pat_3y, 2),
            "cumulative_cfo_3y": round(cum_cfo_3y, 2),
            "divergence_ratio": round(div_3y, 2) if div_3y else "N/A"
        })
    
    result = {
        "ticker": ticker,
        "metric": "Cumulative PAT vs CFO (10-Year + Rolling 3-Year)",
        "cumulative_10y": {
            "pat_crores": round(cumulative_pat, 2),
            "cfo_crores": round(cumulative_cfo, 2),
            "divergence_ratio": round(divergence_ratio, 2) if divergence_ratio else "N/A",
            "flag": pat_cfo_flag
        },
        "rolling_3y": rolling_3y,
        "interpretation": (
            "If PAT >> CFO (ratio > 1.2): high accruals, accounting quality concern. "
            "Healthy range: 0.8–1.2."
        )
    }
    
    return json.dumps(result, indent=2)


@tool(args_schema=TickerInput)
def cfo_ebitda_consistency(ticker: str) -> str:
    """
    Check CFO/EBITDA ratio consistency across years.
    
    Healthy threshold: CFO/EBITDA >= 0.7 consistently. Below indicates
    cash conversion issues or potential accounting red flags.
    
    Args:
        ticker: Indian stock symbol
    
    Returns:
        JSON string with:
        - yearly_ratios: [{year, cfo, ebitda, ratio, status}]
        - summary: {consistent_years, years_below_threshold, flag}
        - interpretation: Text explanation
    
    Monetary values in ₹ Crores.
    """
    data = _fetch_financials(ticker, years=10)
    if not data or "years" not in data:
        return json.dumps({"error": f"Failed to fetch data for {ticker}"}, indent=2)
    
    years_list = sorted(data["years"], key=lambda x: x.get("year", 0))
    
    yearly_ratios = []
    below_threshold = 0
    
    for year_data in years_list:
        cfo = _safe_float(year_data.get("cfo"))
        ebitda = _safe_float(year_data.get("ebitda"))
        ratio = _safe_divide(cfo, ebitda)
        
        status = "✓ HEALTHY" if ratio and ratio >= 0.7 else "⚠️ BELOW 0.7"
        if ratio and ratio < 0.7:
            below_threshold += 1
        
        yearly_ratios.append({
            "year": year_data.get("year"),
            "cfo_crores": round(cfo, 2) if cfo else "N/A",
            "ebitda_crores": round(ebitda, 2) if ebitda else "N/A",
            "ratio": round(ratio, 2) if ratio else "N/A",
            "status": status
        })
    
    consistent_years = len(yearly_ratios) - below_threshold
    
    result = {
        "ticker": ticker,
        "metric": "CFO / EBITDA Consistency (threshold >= 0.7)",
        "yearly_ratios": yearly_ratios,
        "summary": {
            "total_years": len(yearly_ratios),
            "consistent_years": consistent_years,
            "years_below_threshold": below_threshold,
            "flag": "✓ CONSISTENT" if below_threshold <= 1 else "⚠️ CONCERNING"
        },
        "interpretation": (
            "CFO/EBITDA < 0.7: cash conversion issue or accrual manipulation. "
            "Consistent > 0.7: strong cash generation."
        )
    }
    
    return json.dumps(result, indent=2)


@tool(args_schema=TickerInput)
def accrual_profit_conversion(ticker: str) -> str:
    """
    Calculate accrual ratio (balance-sheet method) + Cash Conversion Score.
    
    Accrual Ratio = (ΔCurrent Assets − ΔCash − ΔCurrent Liabilities + ΔCurrent Debt − Depreciation) / Total Assets
    
    High accruals suggest earnings quality issues. Lower is better.
    
    Args:
        ticker: Indian stock symbol
    
    Returns:
        JSON string with:
        - yearly_metrics: [{year, accrual_ratio, cash_conversion_score}]
        - summary: {avg_accrual_ratio, flag}
        - interpretation: Text explanation
    
    Monetary values in ₹ Crores.
    """
    data = _fetch_financials(ticker, years=10)
    if not data or "years" not in data:
        return json.dumps({"error": f"Failed to fetch data for {ticker}"}, indent=2)
    
    years_list = sorted(data["years"], key=lambda x: x.get("year", 0))
    
    yearly_metrics = []
    accrual_ratios = []
    
    for i, year_data in enumerate(years_list):
        pat = _safe_float(year_data.get("pat"))
        cfo = _safe_float(year_data.get("cfo"))
        total_assets = _safe_float(year_data.get("total_assets"))
        
        # Simplified accrual: (PAT - CFO) / Total Assets
        # Full balance-sheet method requires asset/liability changes
        if pat is not None and cfo is not None and total_assets and total_assets > 0:
            accrual_ratio = (pat - cfo) / total_assets
        else:
            accrual_ratio = None
        
        # Cash Conversion Score: CFO / PAT (higher is better)
        cash_conv = _safe_divide(cfo, pat)
        
        status = "⚠️ HIGH ACCRUAL" if accrual_ratio and accrual_ratio > 0.05 else "✓ NORMAL"
        
        if accrual_ratio is not None:
            accrual_ratios.append(accrual_ratio)
        
        yearly_metrics.append({
            "year": year_data.get("year"),
            "accrual_ratio": round(accrual_ratio, 3) if accrual_ratio else "N/A",
            "cash_conversion_score": round(cash_conv, 2) if cash_conv else "N/A",
            "status": status
        })
    
    avg_accrual = statistics.mean(accrual_ratios) if accrual_ratios else None
    
    result = {
        "ticker": ticker,
        "metric": "Accrual Ratio + Cash Conversion Score",
        "yearly_metrics": yearly_metrics,
        "summary": {
            "average_accrual_ratio": round(avg_accrual, 3) if avg_accrual else "N/A",
            "flag": "✓ HEALTHY" if avg_accrual and avg_accrual < 0.05 else "⚠️ ELEVATED"
        },
        "interpretation": (
            "Accrual ratio < 5%: high-quality earnings. "
            "> 5%: potential accrual manipulation or accounting risk."
        )
    }
    
    return json.dumps(result, indent=2)


@tool(args_schema=TickerInput)
def depreciation_volatility(ticker: str) -> str:
    """
    Analyze depreciation as % of sales for year-on-year stability.
    
    Sudden spikes/drops in depreciation % may indicate asset write-offs,
    changes in accounting policy, or capex timing issues.
    
    Args:
        ticker: Indian stock symbol
    
    Returns:
        JSON string with:
        - yearly_metrics: [{year, depreciation, sales, deprec_pct_sales}]
        - summary: {avg_deprec_pct, coefficient_of_variation, flag}
        - interpretation: Text explanation
    
    Monetary values in ₹ Crores.
    """
    data = _fetch_financials(ticker, years=10)
    if not data or "years" not in data:
        return json.dumps({"error": f"Failed to fetch data for {ticker}"}, indent=2)
    
    years_list = sorted(data["years"], key=lambda x: x.get("year", 0))
    
    yearly_metrics = []
    deprec_pcts = []
    
    for year_data in years_list:
        depreciation = _safe_float(year_data.get("depreciation"))
        sales = _safe_float(year_data.get("sales"))
        
        deprec_pct = _safe_divide(depreciation, sales)
        if deprec_pct is not None:
            deprec_pcts.append(deprec_pct * 100)  # Convert to percentage
        
        yearly_metrics.append({
            "year": year_data.get("year"),
            "depreciation_crores": round(depreciation, 2) if depreciation else "N/A",
            "sales_crores": round(sales, 2) if sales else "N/A",
            "depreciation_pct_of_sales": round(deprec_pct * 100, 2) if deprec_pct else "N/A"
        })
    
    avg_pct = statistics.mean(deprec_pcts) if deprec_pcts else None
    cv = _coefficient_of_variation(deprec_pcts)
    
    flag = "⚠️ VOLATILE" if cv and cv > 0.3 else "✓ STABLE"
    
    result = {
        "ticker": ticker,
        "metric": "Depreciation Volatility (% of Sales)",
        "yearly_metrics": yearly_metrics,
        "summary": {
            "average_depreciation_pct": round(avg_pct, 2) if avg_pct else "N/A",
            "coefficient_of_variation": round(cv, 2) if cv else "N/A",
            "flag": flag
        },
        "interpretation": (
            "Stable depreciation %: consistent asset base & accounting. "
            "High volatility: potential accounting changes, write-offs, or capex lumps."
        )
    }
    
    return json.dumps(result, indent=2)


@tool(args_schema=TickerInput)
def cash_return_vs_riskfree(ticker: str) -> str:
    """
    Check whether cash balances earn at least the 10-year risk-free (G-Sec) yield.
    
    If cash returns < risk-free rate: either inefficient capital allocation
    (hoarding) or market conditions issue.
    
    Args:
        ticker: Indian stock symbol
    
    Returns:
        JSON string with:
        - yearly_analysis: [{year, cash_balance, risk_free_rate, cash_return_pct}]
        - summary: {years_below_riskfree, flag}
        - interpretation: Text explanation
    
    Monetary values in ₹ Crores. Rates in decimals (0.072 = 7.2%).
    """
    data = _fetch_financials(ticker, years=10)
    if not data or "years" not in data:
        return json.dumps({"error": f"Failed to fetch data for {ticker}"}, indent=2)
    
    years_list = sorted(data["years"], key=lambda x: x.get("year", 0))
    
    yearly_analysis = []
    below_riskfree = 0
    
    for year_data in years_list:
        cash = _safe_float(year_data.get("cash"))
        interest_income = _safe_float(year_data.get("interest_income"))
        risk_free_rate = _safe_float(year_data.get("risk_free_rate"))
        
        # Cash return = interest_income / cash (if available)
        cash_return = _safe_divide(interest_income, cash)
        
        status = "✓ ABOVE RISK-FREE" if (
            cash_return and risk_free_rate and cash_return >= risk_free_rate
        ) else "⚠️ BELOW RISK-FREE"
        
        if cash_return and risk_free_rate and cash_return < risk_free_rate:
            below_riskfree += 1
        
        yearly_analysis.append({
            "year": year_data.get("year"),
            "cash_balance_crores": round(cash, 2) if cash else "N/A",
            "interest_income_crores": round(interest_income, 2) if interest_income else "N/A",
            "risk_free_rate_pct": round(risk_free_rate * 100, 2) if risk_free_rate else "N/A",
            "cash_return_pct": round(cash_return * 100, 2) if cash_return else "N/A",
            "status": status
        })
    
    result = {
        "ticker": ticker,
        "metric": "Cash Balance Returns vs 10Y Risk-Free Rate",
        "yearly_analysis": yearly_analysis,
        "summary": {
            "total_years": len(yearly_analysis),
            "years_earning_below_riskfree": below_riskfree,
            "flag": "⚠️ INEFFICIENT ALLOCATION" if below_riskfree > len(yearly_analysis) / 2 else "✓ REASONABLE"
        },
        "interpretation": (
            "If cash return consistently < risk-free rate: cash hoarding / poor capital allocation. "
            "Should at minimum match G-Sec yields."
        )
    }
    
    return json.dumps(result, indent=2)


@tool(args_schema=TickerInput)
def fcfe_lumpiness(ticker: str) -> str:
    """
    Analyze FCFE (Free Cash Flow to Equity) generation consistency.
    
    FCFE = CFO − CapEx + Net Debt Issuance
    
    High coefficient of variation indicates lumpy FCF, absent FCF, or
    irregular dividend sustainability.
    
    Args:
        ticker: Indian stock symbol
    
    Returns:
        JSON string with:
        - yearly_metrics: [{year, cfo, capex, debt_repayment, fcfe}]
        - summary: {avg_fcfe, coefficient_of_variation, flag}
        - interpretation: Text explanation
    
    Monetary values in ₹ Crores.
    """
    data = _fetch_financials(ticker, years=10)
    if not data or "years" not in data:
        return json.dumps({"error": f"Failed to fetch data for {ticker}"}, indent=2)
    
    years_list = sorted(data["years"], key=lambda x: x.get("year", 0))
    
    yearly_metrics = []
    fcfe_values = []
    
    for year_data in years_list:
        cfo = _safe_float(year_data.get("cfo"))
        capex = _safe_float(year_data.get("capex"))
        debt_repayment = _safe_float(year_data.get("debt_repayment"))
        equity_raised = _safe_float(year_data.get("equity_raised"))
        
        # Net Debt Issuance (negative = repayment)
        net_debt = (equity_raised or 0) - (debt_repayment or 0)
        
        # FCFE = CFO - CapEx + Net Debt Issuance
        if cfo is not None and capex is not None:
            fcfe = cfo - capex + net_debt
            fcfe_values.append(fcfe)
        else:
            fcfe = None
        
        yearly_metrics.append({
            "year": year_data.get("year"),
            "cfo_crores": round(cfo, 2) if cfo else "N/A",
            "capex_crores": round(capex, 2) if capex else "N/A",
            "net_debt_issuance_crores": round(net_debt, 2),
            "fcfe_crores": round(fcfe, 2) if fcfe else "N/A"
        })
    
    avg_fcfe = statistics.mean(fcfe_values) if fcfe_values else None
    cv = _coefficient_of_variation(fcfe_values)
    
    flag = "⚠️ LUMPY FCF" if cv and cv > 0.5 else "✓ CONSISTENT"
    
    result = {
        "ticker": ticker,
        "metric": "FCFE Lumpiness & Trend Analysis",
        "yearly_metrics": yearly_metrics,
        "summary": {
            "average_fcfe_crores": round(avg_fcfe, 2) if avg_fcfe else "N/A",
            "coefficient_of_variation": round(cv, 2) if cv else "N/A",
            "flag": flag
        },
        "interpretation": (
            "CV < 0.3: stable FCFE, reliable dividends/buybacks. "
            "CV > 0.5: lumpy cash flows, uncertain capital returns. "
            "Negative FCFE: unsustainable dividend/buyback policy."
        )
    }
    
    return json.dumps(result, indent=2)


# =============================================================================
# TOOL CONFIGURATION (for LangChain)
# =============================================================================

PROFIT_QUALITY_TOOLS = [
    cumulative_pat_vs_cfo,
    cfo_ebitda_consistency,
    accrual_profit_conversion,
    depreciation_volatility,
    cash_return_vs_riskfree,
    fcfe_lumpiness,
]


if __name__ == "__main__":
    # Quick test
    print("Testing cumulative_pat_vs_cfo tool...")
    result = cumulative_pat_vs_cfo.invoke({"ticker": "RELIANCE"})
    print(result)
