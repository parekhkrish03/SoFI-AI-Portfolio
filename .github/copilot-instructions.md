## Purpose
Help an AI coding agent become productive quickly in this repository by describing the project's architecture, conventions, and integration points.

## Big Picture
- **What:** A LangChain-compatible tool for fetching Indian stock market financial data.
- **Main component:**
  - `ac_financial_tool.py`: Single tool file that fetches complete financial data from AC Financial Data API and returns a formatted report string.

## Patterns & Conventions (project-specific)
- Tools use the `@tool` decorator from `langchain_core.tools` with Pydantic input schemas.
- Input validation is done via Pydantic `BaseModel` (see `CompanyFinancialsInput`).
- Tools return a single formatted `str` report (never print, always return).
- Configuration (API URL, API key, timeout) is loaded from environment variables via `python-dotenv`.

## Architecture

```
ac_financial_tool.py
├── Configuration (BASE_URL, API_KEY from .env)
├── Input Schema (CompanyFinancialsInput - Pydantic model)
├── Helper Functions
│   ├── _get_headers() - API authentication
│   ├── _fetch_company_data() - HTTP request
│   ├── _format_currency() - Format numbers
│   ├── _safe_float() - Safe type conversion
│   └── _safe_ratio() - Safe division
├── Main Tool
│   └── get_company_financials() - @tool decorated function
└── Tool Config (TOOL_CONFIG dict for LangChain)
```

## Key Integration Points
- **Environment Variables:** `AC_API_KEY` (required), `AC_API_BASE_URL` (optional), `AC_API_TIMEOUT` (optional)
- **API Endpoint:** `https://ac-api-server.vercel.app/server/company/{symbol}`
- **API Documentation:** https://sofixaca.vercel.app/

## Using This Tool in an Agent

```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from ac_financial_tool import get_company_financials

llm = ChatOpenAI(model="gpt-4o")
tools = [get_company_financials]
agent = create_react_agent(llm, tools)
```

## Using as a Standalone Function

```python
from ac_financial_tool import get_company_financials

result = get_company_financials.invoke({"symbol": "RELIANCE.NS"})
print(result)
```

## API Response Fields Used
The tool extracts these fields from `/server/company/{symbol}`:
- Company: `company_name`, `sector`, `ceo_name`, `nse_code`, `listing_date`
- Income: `revenue`, `costOfRevenue`, `grossProfit`, `operatingIncome`, `netIncome`, `ebitda`, `eps`
- Balance Sheet: `totalAssets`, `inventory`, `netReceivables`, `accountPayables`, `totalDebt`, `totalEquity`
- Cash Flow: `operatingCashFlow`, `freeCashFlow`, `capitalExpenditure`, `dividendsPaid`
- Valuation: `marketCapitalization`, `enterpriseValue`, `weightedAverageShsOut`

## Common Edit Locations
- **Add new metrics:** Edit the data extraction section in `get_company_financials()` (around line 150+)
- **Change formatting:** Edit `_format_currency()` helper function
- **Add input parameters:** Modify `CompanyFinancialsInput` Pydantic model

## Run / Debug

```bash
# Activate virtualenv
.venv\Scripts\activate

# Test the tool
python ac_financial_tool.py
```

## Dependencies
- `requests` - HTTP client
- `python-dotenv` - Load .env file
- `langchain-core` - Tool decorator and schemas
- `pydantic` - Input validation 
