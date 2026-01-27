# AC Financial Tool

A LangChain-compatible tool for fetching comprehensive financial data from the AC Financial Data API (Indian Stock Market - NSE/BSE).

## Features

- Complete financial data for Indian stocks (NSE/BSE)
- Income statement, balance sheet, cash flow metrics
- Valuation metrics (market cap, enterprise value)
- Efficiency metrics (DSI, DSO, DPO, Cash Conversion Cycle)
- Financial ratios (current ratio, debt-to-equity, ROE, ROA)
- Pydantic input schema for LangChain/LangGraph integration

## Prerequisites

- Python 3.10+
- AC API Key (contact the API provider)

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Add your API key to `.env`:
   ```env
   AC_API_KEY=your_api_key_here
   ```

## Usage

### As a Standalone Function

```python
from ac_financial_tool import get_company_financials

# Get financial data for Reliance Industries (NSE)
result = get_company_financials.invoke({"symbol": "RELIANCE.NS"})
print(result)

# Get data for a specific year
result = get_company_financials.invoke({
    "symbol": "TCS.NS",
    "calendar_year": 2024
})
print(result)
```

### In a LangGraph Agent

```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from ac_financial_tool import get_company_financials

# Create LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Register the tool
tools = [get_company_financials]

# Create agent
agent = create_react_agent(llm, tools)

# Use the agent
response = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze financials for RELIANCE.NS"}]
})
```

### Tool Configuration

The tool exposes a configuration object for LangChain:

```python
from ac_financial_tool import TOOL_CONFIG

print(TOOL_CONFIG)
# {
#   "name": "get_company_financials",
#   "description": "Fetch comprehensive financial data...",
#   "schema": { ... }  # Pydantic JSON schema
# }
```

## Input Schema

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` | string | Yes | Stock symbol with exchange suffix (.NS for NSE, .BO for BSE) |
| `calendar_year` | integer | No | Specific year (2022-2025). Returns latest if not provided |

## Example Symbols

- `RELIANCE.NS` - Reliance Industries (NSE)
- `TCS.NS` / `TCS.BO` - Tata Consultancy Services
- `INFY.NS` - Infosys
- `HDFCBANK.NS` - HDFC Bank
- `ITC.NS` - ITC Limited

## API Documentation

Full API documentation: https://sofixaca.vercel.app/

## Output

Returns a single formatted string containing:

- Company Overview (name, sector, CEO, listing date)
- Income Statement (revenue, profit, EPS, margins)
- Balance Sheet (assets, liabilities, equity)
- Cash Flow Statement (operating, investing, financing)
- Valuation Metrics (market cap, enterprise value)
- Efficiency Metrics (DSI, DSO, DPO, CCC)
- Financial Ratios (current ratio, debt/equity, ROE, ROA)
