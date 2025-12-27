"""Cost of Debt Analysis Tool - Agent-callable functions for LangGraph orchestration"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import requests

load_dotenv()

@dataclass
class CostOfDebtYear:
    year: int
    interest_expense: float
    short_term_debt: float
    long_term_debt: float
    total_debt: float
    cost_of_debt: Optional[float]
    risk_flag: bool
    notes: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CostOfDebtAnalysis:
    symbol: str
    company_name: str
    currency: str
    years_analyzed: List[CostOfDebtYear]
    average_cost_of_debt: Optional[float]
    trend: str
    overall_risk_level: str
    risk_flags: List[str]
    document_links: List[Dict[str, str]]
    agent_summary: str
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "currency": self.currency,
            "years_analyzed": [y.to_dict() for y in self.years_analyzed],
            "average_cost_of_debt": self.average_cost_of_debt,
            "trend": self.trend,
            "overall_risk_level": self.overall_risk_level,
            "risk_flags": self.risk_flags,
            "document_links": self.document_links,
            "agent_summary": self.agent_summary
        }
    
    def get_langgraph_schema(self) -> Dict:
        return {
            "tool": "cost_of_debt_analysis",
            "company": {
                "symbol": self.symbol,
                "name": self.company_name,
                "currency": self.currency
            },
            "metrics": {
                "average_cost_of_debt_pct": round(self.average_cost_of_debt * 100, 2) if self.average_cost_of_debt else None,
                "trend": self.trend,
                "risk_level": self.overall_risk_level
            },
            "yearly_data": [
                {
                    "year": y.year,
                    "cost_of_debt_pct": round(y.cost_of_debt * 100, 2) if y.cost_of_debt else None,
                    "total_debt": y.total_debt,
                    "interest_expense": y.interest_expense,
                    "risk_flag": y.risk_flag
                }
                for y in self.years_analyzed
            ],
            "flags": {
                "has_risk": len(self.risk_flags) > 0,
                "risk_count": len(self.risk_flags),
                "risk_details": self.risk_flags
            },
            "supporting_docs": self.document_links,
            "agent_interpretation": self.agent_summary
        }


class ACFinancialClient:
    BASE_URL = "https://ac-api-server.vercel.app"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AC_API_KEY")
        if not self.api_key:
            raise ValueError("AC_API_KEY required")
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    
    def _request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success":
                raise ValueError(f"API error: {data.get('message', 'Unknown')}")
            api_data = data.get("data", {})
            if isinstance(api_data, dict) and "records" in api_data:
                return api_data.get("records", [])
            elif isinstance(api_data, list):
                return api_data
            return []
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise ValueError("Invalid API key")
            elif response.status_code == 404:
                raise ValueError(f"Symbol not found")
            raise ValueError(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error: {e}")
    
    def get_income_statement(self, symbol: str, year: Optional[int] = None) -> List[Dict]:
        endpoint = f"/server/company/pnl/{symbol}"
        params = {"calendarYear": year} if year else None
        return self._request(endpoint, params)
    
    def get_balance_sheet(self, symbol: str, year: Optional[int] = None) -> List[Dict]:
        endpoint = f"/server/company/balancesheet/{symbol}"
        params = {"calendarYear": year} if year else None
        return self._request(endpoint, params)
    
    def get_document_links(self, symbol: str) -> List[Dict]:
        try:
            endpoint = f"/server/company/documents/{symbol}"
            return self._request(endpoint)
        except (ValueError, Exception):
            return []


def get_income_statement(symbol: str, year: Optional[int] = None, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    client = ACFinancialClient(api_key=api_key)
    return client.get_income_statement(symbol, year)

def get_balance_sheet(symbol: str, year: Optional[int] = None, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    client = ACFinancialClient(api_key=api_key)
    return client.get_balance_sheet(symbol, year)

def get_document_links(symbol: str, api_key: Optional[str] = None) -> List[Dict[str, str]]:
    client = ACFinancialClient(api_key=api_key)
    return client.get_document_links(symbol)


def _extract_financial_field(records: List[Dict], field_name: str, year: int) -> Optional[float]:
    for record in records:
        # Handle both int and string year formats
        record_year = record.get("calendarYear")
        if record_year is not None:
            try:
                record_year = int(record_year)
            except (ValueError, TypeError):
                continue
            
            if record_year == year:
                value = record.get(field_name)
                if value is not None:
                    try:
                        # Handle both string and numeric values
                        return float(value)
                    except (ValueError, TypeError):
                        pass
    return None

def _calculate_cost_of_debt(interest_expense: Optional[float], debt_current: Optional[float], debt_previous: Optional[float]) -> Optional[float]:
    if interest_expense is None:
        return None
    
    # Need at least one debt value
    if debt_current is None and debt_previous is None:
        return None
    
    # Calculate average debt
    if debt_current is not None and debt_previous is not None:
        avg_debt = (debt_current + debt_previous) / 2
    elif debt_current is not None:
        avg_debt = debt_current
    else:
        avg_debt = debt_previous
    
    # Avoid division by zero or negative debt
    if avg_debt <= 0:
        return None
    
    # Interest expense is typically reported as positive
    # Make sure we use absolute value
    interest_abs = abs(interest_expense)
    
    return interest_abs / avg_debt

def _detect_trend(yearly_costs: List[Optional[float]]) -> str:
    valid_costs = [c for c in yearly_costs if c is not None]
    if len(valid_costs) < 2:
        return "insufficient_data"
    mid = len(valid_costs) // 2
    first_half_avg = sum(valid_costs[:mid]) / len(valid_costs[:mid]) if mid > 0 else 0
    second_half_avg = sum(valid_costs[mid:]) / len(valid_costs[mid:])
    change = second_half_avg - first_half_avg
    if change > 0.005:
        return "increasing"
    elif change < -0.005:
        return "decreasing"
    else:
        return "stable"

def _assess_risk_level(yearly_analyses: List[CostOfDebtYear], average_cost: Optional[float]) -> str:
    if not yearly_analyses or average_cost is None:
        return "unknown"
    risk_count = sum(1 for y in yearly_analyses if y.risk_flag)
    if average_cost > 0.12 or risk_count >= len(yearly_analyses) * 0.75:
        return "critical"
    if average_cost > 0.10 or risk_count >= len(yearly_analyses) * 0.5:
        return "high"
    if risk_count > 0:
        return "moderate"
    return "low"

def analyze_cost_of_debt(symbol: str, years: List[int], risk_threshold: float = 0.10, api_key: Optional[str] = None) -> CostOfDebtAnalysis:
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Invalid symbol")
    
    if not years or not isinstance(years, list) or len(years) == 0:
        raise ValueError("Years must be a non-empty list")
    
    # Sort years chronologically
    years_sorted = sorted(years)
    
    # Initialize client
    client = ACFinancialClient(api_key=api_key)
    
    # Fetch all required data
    income_statements = client.get_income_statement(symbol)
    balance_sheets = client.get_balance_sheet(symbol)
    document_links = client.get_document_links(symbol)
    
    if not income_statements or not balance_sheets:
        raise ValueError(f"Insufficient financial data for {symbol}")
    
    # Extract company metadata
    latest_record = income_statements[0] if income_statements else balance_sheets[0]
    company_name = latest_record.get("symbol", symbol)
    currency = latest_record.get("reportedCurrency", "INR")
    
    # Analyze each year
    yearly_analyses: List[CostOfDebtYear] = []
    debt_values_by_year: Dict[int, float] = {}
    
    for year in years_sorted:
        # Extract interest expense from income statement
        interest_expense = _extract_financial_field(
            income_statements, 
            "interestExpense", 
            year
        )
        
        # Extract debt from balance sheet
        short_term_debt = _extract_financial_field(
            balance_sheets,
            "shortTermDebt",
            year
        ) or 0.0
        
        long_term_debt = _extract_financial_field(
            balance_sheets,
            "longTermDebt",
            year
        ) or 0.0
        
        total_debt = short_term_debt + long_term_debt
        debt_values_by_year[year] = total_debt
        
        # Calculate cost of debt
        # Need previous year's debt for average calculation
        previous_year = year - 1
        previous_debt = debt_values_by_year.get(previous_year)
        
        cost_of_debt = _calculate_cost_of_debt(
            interest_expense,
            total_debt,
            previous_debt
        )
        
        # Risk assessment
        risk_flag = False
        notes = []
        
        if cost_of_debt is None:
            notes.append("Cost of debt could not be calculated")
            if interest_expense is None:
                notes.append("Missing interest expense data")
            if total_debt <= 0:
                notes.append("Zero or negative total debt")
        else:
            if cost_of_debt > risk_threshold:
                risk_flag = True
                notes.append(f"Cost of debt {cost_of_debt:.2%} exceeds threshold {risk_threshold:.2%}")
        
        if total_debt == 0:
            notes.append("Company has no debt in this period")
        
        yearly_analyses.append(CostOfDebtYear(
            year=year,
            interest_expense=interest_expense or 0.0,
            short_term_debt=short_term_debt,
            long_term_debt=long_term_debt,
            total_debt=total_debt,
            cost_of_debt=cost_of_debt,
            risk_flag=risk_flag,
            notes=notes
        ))
    
    # Calculate average cost of debt (excluding None values)
    valid_costs = [y.cost_of_debt for y in yearly_analyses if y.cost_of_debt is not None]
    average_cost = sum(valid_costs) / len(valid_costs) if valid_costs else None
    
    # Detect trend
    trend = _detect_trend([y.cost_of_debt for y in yearly_analyses])
    
    # Overall risk assessment
    overall_risk = _assess_risk_level(yearly_analyses, average_cost)
    
    # Compile risk flags
    risk_flags = []
    if average_cost and average_cost > risk_threshold:
        risk_flags.append(f"Average cost of debt {average_cost:.2%} exceeds {risk_threshold:.2%}")
    
    if trend == "increasing":
        risk_flags.append("Cost of debt is increasing over time")
    
    if overall_risk in ["high", "critical"]:
        risk_flags.append(f"Overall risk level assessed as {overall_risk}")
    
    # Check for missing data
    missing_years = [y.year for y in yearly_analyses if y.cost_of_debt is None]
    if missing_years:
        risk_flags.append(f"Missing cost of debt data for years: {missing_years}")
    
    # Generate agent summary
    if average_cost:
        summary = (
            f"Cost of debt analysis for {company_name} ({symbol}): "
            f"Average cost {average_cost:.2%} across {len(years_sorted)} years. "
            f"Trend: {trend}. Risk level: {overall_risk}."
        )
    else:
        summary = (
            f"Cost of debt analysis for {company_name} ({symbol}): "
            f"Insufficient data to calculate average cost. "
            f"Risk level: {overall_risk}."
        )
    
    if risk_flags:
        summary += f" Flags: {len(risk_flags)} risk factors identified."
    
    return CostOfDebtAnalysis(
        symbol=symbol,
        company_name=company_name,
        currency=currency,
        years_analyzed=yearly_analyses,
        average_cost_of_debt=average_cost,
        trend=trend,
        overall_risk_level=overall_risk,
        risk_flags=risk_flags,
        document_links=document_links,
        agent_summary=summary
    )


def cost_of_debt_node(state: Dict) -> Dict:
    try:
        symbol = state.get("symbol")
        years = state.get("years", [2022, 2023, 2024])
        risk_threshold = state.get("risk_threshold", 0.10)
        
        if not symbol:
            raise ValueError("Symbol required in state")
        
        # Perform analysis
        result = analyze_cost_of_debt(
            symbol=symbol,
            years=years,
            risk_threshold=risk_threshold
        )
        
        # Return enhanced state for next agent
        return {
            **state,
            "cost_of_debt_analysis": result.get_langgraph_schema(),
            "cost_of_debt_summary": result.agent_summary,
            "cost_of_debt_flags": {
                "has_risk": len(result.risk_flags) > 0,
                "risk_level": result.overall_risk_level,
                "trend": result.trend,
                "details": result.risk_flags
            },
            "cost_of_debt_metrics": {
                "average_cost_pct": round(result.average_cost_of_debt * 100, 2) if result.average_cost_of_debt else None,
                "yearly_costs": [
                    {
                        "year": y.year,
                        "cost_pct": round(y.cost_of_debt * 100, 2) if y.cost_of_debt else None
                    }
                    for y in result.years_analyzed
                ]
            }
        }
        
    except Exception as e:
        return {
            **state,
            "cost_of_debt_error": str(e),
            "cost_of_debt_analysis": None
        }
