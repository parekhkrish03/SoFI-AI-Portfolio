"""
AC Financial Data Tool for LangChain/LangGraph Agents

This module provides LangChain-compatible tools for fetching and analyzing
financial data from the AC Financial Data API (Indian Stock Market - NSE/BSE).

Usage:
    from ac_financial_tool import get_company_financials

    # As a function
    result = get_company_financials.invoke({"symbol": "RELIANCE.NS"})

    # In a LangGraph agent
    tools = [get_company_financials]
    agent = create_react_agent(llm, tools)
"""

import os
from typing import Optional

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# API Configuration - loaded from environment variables
BASE_URL = os.environ.get("AC_API_BASE_URL", "https://ac-api-server.vercel.app")
API_KEY = os.environ.get("AC_API_KEY")
REQUEST_TIMEOUT = float(os.environ.get("AC_API_TIMEOUT", "12"))


# =============================================================================
# INPUT SCHEMA (Pydantic Model for LangChain)
# =============================================================================

class CompanyFinancialsInput(BaseModel):
    """Input schema for the get_company_financials tool."""
    
    symbol: str = Field(
        description="Indian stock symbol with exchange suffix. "
                    "Use .NS for NSE (e.g., RELIANCE.NS, TCS.NS) or "
                    ".BO for BSE (e.g., RELIANCE.BO, TCS.BO). "
                    "The suffix is REQUIRED."
    )
    calendar_year: Optional[int] = Field(
        default=None,
        description="Optional: Specific calendar year (2022-2025). "
                    "If not provided, returns the latest available data."
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_headers() -> dict:
    """Build request headers with API key authentication."""
    if not API_KEY:
        raise ValueError(
            "AC_API_KEY not found in environment. "
            "Please set it in your .env file or environment variables."
        )
    return {"x-api-key": API_KEY}


def _fetch_company_data(symbol: str) -> dict:
    """
    Fetch complete financial data for a company from the API.
    
    Args:
        symbol: Stock symbol with exchange suffix (e.g., RELIANCE.NS)
    
    Returns:
        dict: API response with status and data
    
    Raises:
        requests.RequestException: If API request fails
    """
    url = f"{BASE_URL}/server/company/{symbol}"
    response = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _format_currency(value: float, currency: str = "INR") -> str:
    """Format a number as currency with appropriate symbol."""
    if value is None:
        return "N/A"
    
    symbol = "Rs." if currency == "INR" else "$"
    
    # Convert to crores for Indian stocks (1 crore = 10 million)
    if currency == "INR" and abs(value) >= 10_000_000:
        crores = value / 10_000_000
        return f"{symbol}{crores:,.2f} Cr"
    
    return f"{symbol}{value:,.2f}"


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_ratio(numerator: float, denominator: float) -> Optional[float]:
    """Safely calculate a ratio, returns None if denominator is zero."""
    if denominator == 0:
        return None
    return numerator / denominator


# =============================================================================
# MAIN TOOL
# =============================================================================

@tool(args_schema=CompanyFinancialsInput)
def get_company_financials(symbol: str, calendar_year: Optional[int] = None) -> str:
    """
    Fetch comprehensive financial data for an Indian stock (NSE/BSE).
    
    This tool retrieves complete financial information including:
    - Company overview (name, sector, description)
    - Income statement metrics (revenue, net income, EPS, margins)
    - Balance sheet data (assets, liabilities, equity, debt)
    - Cash flow metrics (operating, investing, financing cash flows)
    - Valuation metrics (market cap, enterprise value)
    - Efficiency metrics (inventory days, receivables days, payables days)
    
    Args:
        symbol: Stock symbol with exchange suffix (e.g., RELIANCE.NS or TCS.BO)
        calendar_year: Optional specific year (2022-2025)
    
    Returns:
        A formatted string report with all financial metrics.
    """
    
    # Validate symbol format
    symbol = symbol.strip().upper()
    if not symbol.endswith((".NS", ".BO")):
        return (
            f"Error: Invalid symbol format '{symbol}'. "
            "Please use .NS suffix for NSE (e.g., RELIANCE.NS) or "
            ".BO suffix for BSE (e.g., RELIANCE.BO)."
        )
    
    # Check API key
    if not API_KEY:
        return (
            "Error: AC_API_KEY not configured. "
            "Please set it in your .env file."
        )
    
    # Fetch data from API
    try:
        response = _fetch_company_data(symbol)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "Error: Invalid API key. Please check your AC_API_KEY."
        elif e.response.status_code == 404:
            return f"Error: Symbol '{symbol}' not found. Please verify the stock symbol."
        else:
            return f"Error: API request failed with status {e.response.status_code}."
    except requests.exceptions.RequestException as e:
        return f"Error: Could not connect to API. Details: {str(e)}"
    
    # Check response structure
    if response.get("status") != "success" or not response.get("data"):
        return f"Error: No data found for symbol '{symbol}'."
    
    # Get the data records
    records = response["data"]
    if not isinstance(records, list) or len(records) == 0:
        return f"Error: Empty data returned for symbol '{symbol}'."
    
    # Filter by calendar year if specified
    if calendar_year:
        records = [r for r in records if r.get("calendarYear") == calendar_year]
        if not records:
            return f"Error: No data found for {symbol} in year {calendar_year}."
    
    # Use the most recent record (first in list)
    data = records[0]
    
    # Extract all fields with safe defaults
    currency = data.get("reportedCurrency", "INR")
    
    # Company Information
    company_name = data.get("company_name", "N/A")
    sector = data.get("sector", "N/A")
    ceo = data.get("ceo_name", "N/A")
    nse_code = data.get("nse_code", "N/A")
    listing_date = data.get("listing_date", "N/A")
    report_date = data.get("date", "N/A")
    report_year = data.get("calendarYear", "N/A")
    period = data.get("period", "N/A")
    
    # Income Statement Metrics
    revenue = _safe_float(data.get("revenue"))
    cost_of_revenue = _safe_float(data.get("costOfRevenue"))
    gross_profit = _safe_float(data.get("grossProfit"))
    operating_income = _safe_float(data.get("operatingIncome"))
    net_income = _safe_float(data.get("netIncome"))
    ebitda = _safe_float(data.get("ebitda"))
    eps = _safe_float(data.get("eps"))
    
    # Margins (already as ratios from API)
    gross_profit_ratio = _safe_float(data.get("grossProfitRatio"))
    operating_income_ratio = _safe_float(data.get("operatingIncomeRatio"))
    net_income_ratio = _safe_float(data.get("netIncomeRatio"))
    ebitda_ratio = _safe_float(data.get("ebitdaratio"))
    
    # Balance Sheet - Assets
    total_assets = _safe_float(data.get("totalAssets"))
    total_current_assets = _safe_float(data.get("totalCurrentAssets"))
    cash_and_equivalents = _safe_float(data.get("cashAndCashEquivalents"))
    short_term_investments = _safe_float(data.get("shortTermInvestments"))
    inventory = _safe_float(data.get("inventory"))
    net_receivables = _safe_float(data.get("netReceivables"))
    property_plant_equipment = _safe_float(data.get("propertyPlantEquipmentNet"))
    goodwill_and_intangibles = _safe_float(data.get("goodwillAndIntangibleAssets"))
    long_term_investments = _safe_float(data.get("longTermInvestments"))
    
    # Balance Sheet - Liabilities
    total_liabilities = _safe_float(data.get("totalLiabilities"))
    total_current_liabilities = _safe_float(data.get("totalCurrentLiabilities"))
    account_payables = _safe_float(data.get("accountPayables"))
    short_term_debt = _safe_float(data.get("shortTermDebt"))
    long_term_debt = _safe_float(data.get("longTermDebt"))
    total_debt = _safe_float(data.get("totalDebt"))
    
    # Balance Sheet - Equity
    total_equity = _safe_float(data.get("totalEquity"))
    total_stockholders_equity = _safe_float(data.get("totalStockholdersEquity"))
    retained_earnings = _safe_float(data.get("retainedEarnings"))
    
    # Cash Flow Statement
    operating_cash_flow = _safe_float(data.get("operatingCashFlow"))
    investing_cash_flow = _safe_float(data.get("netCashUsedForInvestingActivites"))
    financing_cash_flow = _safe_float(data.get("netCashUsedProvidedByFinancingActivities"))
    capital_expenditure = _safe_float(data.get("capitalExpenditure"))
    free_cash_flow = _safe_float(data.get("freeCashFlow"))
    dividends_paid = _safe_float(data.get("dividendsPaid"))
    
    # Valuation Metrics
    market_cap = _safe_float(data.get("marketCapitalization"))
    enterprise_value = _safe_float(data.get("enterpriseValue"))
    shares_outstanding = _safe_float(data.get("weightedAverageShsOut"))
    
    # Calculate Efficiency Metrics (Working Capital Cycle)
    # Days Sales in Inventory (DSI) = (Inventory / Cost of Revenue) * 365
    dsi = _safe_ratio(inventory, cost_of_revenue)
    dsi = dsi * 365 if dsi else 0
    
    # Days Sales Outstanding (DSO) = (Receivables / Revenue) * 365
    dso = _safe_ratio(net_receivables, revenue)
    dso = dso * 365 if dso else 0
    
    # Days Payable Outstanding (DPO) = (Payables / Cost of Revenue) * 365
    dpo = _safe_ratio(account_payables, cost_of_revenue)
    dpo = dpo * 365 if dpo else 0
    
    # Cash Conversion Cycle (CCC) = DSI + DSO - DPO
    ccc = dsi + dso - dpo
    
    # Determine efficiency status
    if ccc < 30:
        efficiency_status = "Excellent"
    elif ccc < 60:
        efficiency_status = "Good"
    elif ccc < 90:
        efficiency_status = "Average"
    else:
        efficiency_status = "Needs Improvement"
    
    # Calculate Financial Ratios
    current_ratio = _safe_ratio(total_current_assets, total_current_liabilities)
    debt_to_equity = _safe_ratio(total_debt, total_stockholders_equity)
    roe = _safe_ratio(net_income, total_stockholders_equity)
    roa = _safe_ratio(net_income, total_assets)
    
    # Build the report string
    report = f"""
================================================================================
FINANCIAL REPORT: {company_name} ({symbol})
================================================================================

COMPANY OVERVIEW
--------------------------------------------------------------------------------
Company Name      : {company_name}
Stock Symbol      : {symbol}
NSE Code          : {nse_code}
Sector            : {sector}
CEO               : {ceo}
Listing Date      : {listing_date}

REPORT DETAILS
--------------------------------------------------------------------------------
Report Date       : {report_date}
Calendar Year     : {report_year}
Period            : {period}
Currency          : {currency}

INCOME STATEMENT
--------------------------------------------------------------------------------
Revenue           : {_format_currency(revenue, currency)}
Cost of Revenue   : {_format_currency(cost_of_revenue, currency)}
Gross Profit      : {_format_currency(gross_profit, currency)}
Operating Income  : {_format_currency(operating_income, currency)}
EBITDA            : {_format_currency(ebitda, currency)}
Net Income        : {_format_currency(net_income, currency)}
EPS               : Rs.{eps:.2f}

PROFIT MARGINS
--------------------------------------------------------------------------------
Gross Margin      : {gross_profit_ratio * 100:.2f}%
Operating Margin  : {operating_income_ratio * 100:.2f}%
EBITDA Margin     : {ebitda_ratio * 100:.2f}%
Net Profit Margin : {net_income_ratio * 100:.2f}%

BALANCE SHEET - ASSETS
--------------------------------------------------------------------------------
Total Assets          : {_format_currency(total_assets, currency)}
Current Assets        : {_format_currency(total_current_assets, currency)}
  - Cash & Equivalents: {_format_currency(cash_and_equivalents, currency)}
  - Short-term Invest.: {_format_currency(short_term_investments, currency)}
  - Inventory         : {_format_currency(inventory, currency)}
  - Net Receivables   : {_format_currency(net_receivables, currency)}
Non-Current Assets    : {_format_currency(total_assets - total_current_assets, currency)}
  - Property/Plant/Eq.: {_format_currency(property_plant_equipment, currency)}
  - Goodwill/Intang.  : {_format_currency(goodwill_and_intangibles, currency)}
  - Long-term Invest. : {_format_currency(long_term_investments, currency)}

BALANCE SHEET - LIABILITIES & EQUITY
--------------------------------------------------------------------------------
Total Liabilities     : {_format_currency(total_liabilities, currency)}
Current Liabilities   : {_format_currency(total_current_liabilities, currency)}
  - Accounts Payable  : {_format_currency(account_payables, currency)}
  - Short-term Debt   : {_format_currency(short_term_debt, currency)}
Non-Current Liabilities: {_format_currency(total_liabilities - total_current_liabilities, currency)}
  - Long-term Debt    : {_format_currency(long_term_debt, currency)}
Total Debt            : {_format_currency(total_debt, currency)}
Total Equity          : {_format_currency(total_equity, currency)}
Stockholders' Equity  : {_format_currency(total_stockholders_equity, currency)}

CASH FLOW STATEMENT
--------------------------------------------------------------------------------
Operating Cash Flow   : {_format_currency(operating_cash_flow, currency)}
Investing Cash Flow   : {_format_currency(investing_cash_flow, currency)}
Financing Cash Flow   : {_format_currency(financing_cash_flow, currency)}
Capital Expenditure   : {_format_currency(capital_expenditure, currency)}
Free Cash Flow        : {_format_currency(free_cash_flow, currency)}
Dividends Paid        : {_format_currency(dividends_paid, currency)}

VALUATION METRICS
--------------------------------------------------------------------------------
Market Capitalization : {_format_currency(market_cap, currency)}
Enterprise Value      : {_format_currency(enterprise_value, currency)}
Shares Outstanding    : {shares_outstanding:,.0f}

EFFICIENCY METRICS (Working Capital Cycle)
--------------------------------------------------------------------------------
Days Sales in Inventory (DSI)  : {dsi:.1f} days
Days Sales Outstanding (DSO)   : {dso:.1f} days
Days Payable Outstanding (DPO) : {dpo:.1f} days
Cash Conversion Cycle (CCC)    : {ccc:.1f} days
Efficiency Status              : {efficiency_status}

FINANCIAL RATIOS
--------------------------------------------------------------------------------
Current Ratio         : {current_ratio:.2f}x (Current Assets / Current Liabilities)
Debt to Equity        : {debt_to_equity:.2f}x (Total Debt / Stockholders' Equity)
Return on Equity (ROE): {(roe * 100) if roe else 0:.2f}% (Net Income / Equity)
Return on Assets (ROA): {(roa * 100) if roa else 0:.2f}% (Net Income / Assets)

================================================================================
Data Source: AC Financial Data API | NSE/BSE India
================================================================================
"""
    
    return report.strip()


# =============================================================================
# TOOL CONFIGURATION (For LangChain Registry)
# =============================================================================

# This configuration object is automatically read by LangChain
TOOL_CONFIG = {
    "name": "get_company_financials",
    "description": (
        "Fetch comprehensive financial data for Indian stocks (NSE/BSE). "
        "Returns complete financial report including income statement, "
        "balance sheet, cash flow, valuation metrics, and efficiency ratios. "
        "Requires stock symbol with exchange suffix (.NS for NSE, .BO for BSE)."
    ),
    "schema": CompanyFinancialsInput.model_json_schema()
}


# =============================================================================
# DIRECT USAGE (for testing)
# =============================================================================

if __name__ == "__main__":
    # Test the tool directly
    print("Testing AC Financial Tool...")
    print("=" * 60)
    
    # Test with RELIANCE.NS
    result = get_company_financials.invoke({"symbol": "RELIANCE.NS"})
    print(result)
