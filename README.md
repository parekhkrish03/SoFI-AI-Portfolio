# Cost of Debt Analysis Tool

Agent-callable tool for analyzing cost of debt using AC Financial Data API.

## Features
- Fetches income statement and balance sheet data from AC Financial API
- Calculates cost of debt: Interest Expense / Average Total Debt
- Analyzes trends across multiple years
- Risk assessment and flagging
- LangGraph integration ready

## Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Agentic
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install requests python-dotenv
   ```

4. **Configure API key**
   ```bash
   cp .env.example .env
   # Edit .env and add your AC Financial API key
   ```

## Usage

```python
from cost_of_debt_tool import analyze_cost_of_debt

# Analyze a company's cost of debt
result = analyze_cost_of_debt('TCS', [2022, 2023, 2024])

print(f"Company: {result.company_name}")
print(f"Average Cost: {result.average_cost_of_debt * 100:.2f}%")
print(f"Risk Level: {result.overall_risk_level}")
print(f"Trend: {result.trend}")
```

## LangGraph Integration

```python
from cost_of_debt_tool import cost_of_debt_node

# Use in LangGraph workflow
state = {
    "symbol": "TCS",
    "years": [2022, 2023, 2024]
}

updated_state = cost_of_debt_node(state)
```

## API Reference

- **AC Financial API**: https://ac-api-server.vercel.app
- Coverage: NSE/BSE Indian stock exchanges
- Currency: INR (Indian Rupees)

## Files

- `cost_of_debt_tool.py` - Main analysis tool
- `Agent.py` - Reverse DCF valuation tool
- `.env.example` - Environment configuration template
