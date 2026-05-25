# Profit Quality Analysis Tool

**Module 1 of the SoFi Forensic Analysis Toolkit**

A LangChain-compatible forensic analysis tool for Indian stocks (NSE/BSE) that detects earnings manipulation and accounting red flags through 7 sophisticated forensic checks.

---

## 🎯 What This Tool Does

The **Profit Quality Analysis Tool** accepts an Indian stock ticker symbol and performs an in-depth forensic analysis of the company's profit quality and earnings reliability over 4–10 years of historical data.

**Core Principle:** High-quality earnings always convert to actual cash. Accounting manipulators leave detectable traces.

The tool returns a **composite Profit Quality Score (0–100)** with an A–D grade, plus detailed forensic breakdowns for the AI agent and investment team.

---

## 🔍 The 7 Forensic Checks

### 1. **PAT vs CFO Divergence** (25% weight)
**What it detects:** When reported profits significantly exceed actual cash generation.

**Formula:** `Divergence% = (ΣPAT − ΣCFO) / |ΣPAT| × 100`

**Red flags:**
- ✅ PASS: < 10% divergence (healthy)
- ⚠️ WARN: 10–25% divergence (investigate)
- 🚨 FAIL: ≥ 25% divergence (accrual manipulation signals)

**Why it matters:** If cash flow lags profit consistently, profits might be inflated through receivables, inventory buildup, or revenue recognition issues.

---

### 2. **CFO/EBITDA Consistency** (20% weight)
**What it detects:** What % of operating profits actually convert to cash?

**Formula:** `Ratio = Operating Cash Flow / EBITDA`

**Red flags:**
- ✅ PASS: ≥ 0.7 (healthy)
- ⚠️ WARN: 0.5–0.7 (weak)
- 🚨 FAIL: < 0.5 (severe working capital drain)

**Why it matters:** EBITDA is operating profit before financing/taxes. CFO should capture 70%+ of EBITDA. Lower suggests working capital buildup (receivables/inventory) without sales justification.

---

### 3. **Balance-Sheet Accrual Ratio** (20% weight)
**What it detects:** Non-cash profit items (accruals) as % of total assets.

**Formula:**
```
NOA = (Total Assets − Cash) − Total Liabilities
Accrual Ratio = (NOA_current − NOA_prior) / AvgAssets × 100
```

**Red flags:**
- ✅ PASS: < 3% (high-quality earnings)
- ⚠️ WARN: 3–7% (normal accrual levels)
- 🚨 FAIL: ≥ 7% (high-accrual risk)

**Why it matters:** Accruals are the easiest points to manipulate (deferred revenue, questionable receivables, inventory). High accruals often precede earnings reversals.

---

### 4. **Cash Conversion Score** (10% weight)
**What it detects:** What % of reported profit actually becomes cash?

**Formula:** `CCS = (CFO / PAT) × 100`

**Red flags:**
- ✅ PASS: ≥ 70% (good)
- ⚠️ WARN: 50–70% (weak)
- 🚨 FAIL: < 50% (accrual-heavy earnings)

**Why it matters:** Healthy businesses convert 70–110% of profit to cash. Below 50% suggests major non-cash accruals or timing issues.

---

### 5. **Depreciation Rate Volatility** (10% weight)
**What it detects:** Sudden changes in depreciation policy (accounting red flag).

**Formula:**
```
DepRate% = (Depreciation / Net Sales) × 100
σ = Standard Deviation of DepRate across years
```

**Red flags:**
- 🟢 STABLE: σ < 0.5 pp (normal)
- 🟡 WATCH: 0.5–1.0 pp (moderate volatility)
- 🔴 VOLATILE: σ ≥ 1.0 pp (accounting changes)

**Why it matters:** Stable depreciation = predictable asset base. Sharp spikes often precede earnings surprises (asset write-offs, useful-life changes, or impairments).

---

### 6. **Cash Yield vs 10Y G-Sec** (5% weight)
**What it detects:** Whether excess cash is efficiently allocated.

**Formula:**
```
ImpliedYield% = (Interest Income / Cash Balance) × 100
Spread% = ImpliedYield − G-Sec Yield (7.2%)
```

**Red flags:**
- ✅ PASS: Spread ≥ 0% (earning at least risk-free)
- ⚠️ WARN: −1% ≤ Spread < 0% (below benchmark)
- 🚨 FAIL: Spread < −1% (hoarding/mismanagement)

**Why it matters:** Cash hoarding (unable to deploy for growth) suggests management caution or hidden liquidity concerns.

---

### 7. **FCFE Lumpiness & Sustainability** (10% weight)
**What it detects:** Free cash flow to equity sustainability (dividends at risk?).

**Formula:**
```
FCFE = CFO − CapEx + Net Borrowings
Count years with FCFE < 0
```

**Red flags:**
- 🟢 HEALTHY: 0–1 negative years (sustainable)
- 🟡 WATCH: 2–3 negative years (cyclical)
- 🔴 CONCERN: ≥ 4 negative years (unsustainable)

**Why it matters:** If FCFE is negative most years but dividend is stable, it's being funded from cash depletion (unsustainable, likely to be cut).

---

## 📊 Composite Score & Grade

The tool weights all 7 checks and produces a **Profit Quality Score (0–100)**:

| Score Range | Grade | Interpretation |
|---|---|---|
| 80–100 | **A — HIGH QUALITY** | Excellent earnings quality, low manipulation risk |
| 60–79 | **B — ADEQUATE** | Acceptable financials, investigate any flags |
| 40–59 | **C — BELOW PAR** | Multiple concerns, elevated risk |
| 0–39 | **D — POOR QUALITY** | Severe red flags, high manipulation risk |

**Example:**
- RELIANCE score: 70 → Grade B (ADEQUATE)
- Red flags: 1 (PAT vs CFO divergence)
- Interpretation: Good overall, but investigate receivables/inventory buildup

---

## 🚀 How to Use

### Standalone Python
```python
from profit_quality_tool import run_profit_quality_analysis
import json

# Run analysis
result_json = run_profit_quality_analysis.invoke({"ticker": "RELIANCE"})
result = json.loads(result_json)

# Access results
print(result["scorecard"]["grade"])           # "B — ADEQUATE"
print(result["scorecard"]["profit_quality_score"])  # 70.0
print(result["scorecard"]["red_flag_count"])  # 1

# Detailed check breakdown
print(result["checks"]["pat_vs_cfo"]["flag"])  # "🚨 FAIL"
print(result["checks"]["cfo_ebitda"]["value"])  # 0.87
```

### In a LangChain Agent
```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from profit_quality_tool import run_profit_quality_analysis

llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent = create_react_agent(llm, [run_profit_quality_analysis])

response = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Analyze profit quality for HDFCBANK and report red flags"
    }]
})
print(response["messages"][-1]["content"])
```

### Command Line (Quick Test)
```bash
python profit_quality_tool.py INFY
python profit_quality_tool.py HDFCBANK
python profit_quality_tool.py TCS
```

---

## 📥 Input

**Ticker:** Indian stock symbol (NSE/BSE)
- Examples: `RELIANCE`, `INFY`, `HDFCBANK`, `TCS`, `WIPRO`, `SBIN`, `ICICIBANK`
- Format: Just the symbol (e.g., `RELIANCE`). Tool auto-appends `.NS` for NSE.

---

## 📤 Output JSON Structure

```json
{
  "ticker": "RELIANCE",
  "analysis_date": "2026-05-25",
  "years_of_data": 4,
  "year_range": "2022 – 2025",
  
  "scorecard": {
    "profit_quality_score": 70.0,
    "max_score": 100,
    "grade": "B — ADEQUATE",
    "red_flag_count": 1,
    "component_scores": {
      "pat_vs_cfo": {"raw_score": 0, "weight": 0.25, "weighted_contribution": 0.0},
      "cfo_ebitda": {"raw_score": 100, "weight": 0.2, "weighted_contribution": 20.0},
      ...
    }
  },
  
  "checks": {
    "pat_vs_cfo": {
      "name": "PAT vs CFO Divergence (10Y + Rolling 3Y)",
      "value": 111.18,
      "unit": "%",
      "flag": "🚨 FAIL",
      "score": 0,
      "detail": "Cumulative PAT: 266676.0, CFO: 563177.0"
    },
    "cfo_ebitda": { ... },
    "accrual": { ... },
    "ccs": { ... },
    "dep_volatility": { ... },
    "cash_vs_rfr": { ... },
    "fcfe": { ... }
  },
  
  "data_warnings": [],
  "module": "profit_quality",
  "toolkit": "SoFi Forensic Analysis | AI Portfolio Analyser"
}
```

---

## ⚙️ Setup Requirements

### 1. Environment Variables (`.env`)
```
STOCK_API_BASE_URL=https://ac-api-server.vercel.app
STOCK_API_KEY=<your_api_key>
API_TIMEOUT=12
DEFAULT_RISK_FREE_RATE=0.072
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

**Required packages:**
- `requests` — API calls
- `python-dotenv` — Load .env
- `langchain-core` — @tool decorator
- `pydantic` — Input validation

### 3. Get Your API Key
- **API Provider:** AC Financial Data API (covers Indian stock market)
- **Documentation:** https://sofixaca.vercel.app/
- **Contact:** Reach out to your portfolio manager or API provider

---

## 📈 Real-World Example

### Input
```python
run_profit_quality_analysis.invoke({"ticker": "RELIANCE"})
```

### Output (Excerpt)
```json
{
  "ticker": "RELIANCE",
  "scorecard": {
    "profit_quality_score": 70.0,
    "grade": "B — ADEQUATE"
  },
  "checks": {
    "pat_vs_cfo": {
      "flag": "🚨 FAIL",
      "detail": "PAT exceeded CFO by 111% cumulatively"
    },
    "cfo_ebitda": {
      "flag": "✅ PASS",
      "value": 0.87,
      "detail": "Healthy cash conversion"
    },
    "accrual": {
      "flag": "✅ PASS",
      "value": 0.72,
      "detail": "Excellent earnings quality"
    }
  }
}
```

### Interpretation
- **Score 70 (B grade):** Overall acceptable profits, but investigate
- **1 Red Flag:** PAT exceeded CFO by 111% — large divergence suggests accrual buildup
- **Action:** Request detailed breakdown of:
  - Receivables growth (vs revenue growth)
  - Inventory levels (vs sales growth)
  - Deferred revenue trends

---

## 🔴 Red Flag Thresholds & Why They Matter

| Red Flag | Threshold | Concern |
|---|---|---|
| **PAT vs CFO** | > 25% divergence | Major accrual manipulation risk |
| **CFO/EBITDA** | < 0.5 ratio | Working capital drain / fake sales |
| **Accrual Ratio** | > 7% | Heavy reliance on non-cash items |
| **CCS** | < 50% | Most profit is accruals, not cash |
| **Depreciation** | σ > 1.0 pp | Accounting policy changes |
| **Cash Yield** | < −1% spread | Hoarding cash / liquidity concern |
| **FCFE Negative** | >= 4 of 10 years | Dividend unsustainable |

---

## 📝 Data Requirements

The tool requires 10 years of annual financial data (or as many years available):

**Income Statement:**
- Net Income (PAT)
- EBITDA
- Depreciation & Amortization
- Revenue (Net Sales)
- Interest Income

**Balance Sheet:**
- Total Assets
- Total Liabilities
- Cash & Cash Equivalents

**Cash Flow Statement:**
- Operating Cash Flow (CFO)
- Capital Expenditures (CapEx)
- Net Change in Cash

**Valuation:**
- Risk-Free Rate (10Y G-Sec yield, defaults to 7.2%)

All monetary values in **₹ Crores** (Indian standard).

---

## 🧪 Testing

### Quick Test (After Setup)
```bash
python profit_quality_tool.py INFY
```

**Expected output:** JSON with scorecard and 7 checks

### Example Tickers to Test
- `RELIANCE` — Oil & gas major
- `INFY` — IT services
- `HDFCBANK` — Banking
- `TCS` — IT consulting
- `TATASTEEL` — Steel
- `BAJAJFINANCE` — Finance

---

## ⚠️ Error Handling

The tool returns structured error messages:

| Error | Cause | Fix |
|---|---|---|
| `CONFIGURATION_ERROR` | Missing `.env` keys | Set `STOCK_API_BASE_URL` and `STOCK_API_KEY` |
| `TICKER_NOT_FOUND` | Invalid ticker or API returns 404 | Verify ticker format (use NSE of BSE symbol) |
| `API_ERROR` | Timeout or rate limit | Wait and retry; check internet |
| `UNEXPECTED_ERROR` | Other exception | Check `.env` keys and Python dependencies |

---

## 🔗 Integration with SoFi Toolkit

This tool is **Module 1** of a larger forensic analysis framework:

**Future modules (same pattern):**
- Revenue Quality Tool — Revenue recognition, channel stuffing
- Balance Sheet Tool — Asset quality, goodwill, intangibles
- Debt Leverage Tool — Debt structure, interest cover
- Working Capital Tool — WC cycle, receivables, inventory
- Related-Party Tool — RPT tunnelling, promoter pledges
- Management Quality Tool — Auditor changes, SEBI orders
- Capital Allocation Tool — ROCE, dividend policy

All modules will be orchestrated by a **LangChain agent** that synthesizes individual scores into a comprehensive forensic report.

---

## 📚 Academic Foundation

The 7 checks are based on peer-reviewed financial forensics research:

1. **PAT vs CFO** — Sloan (1996) *"Do stock prices fully reflect information in accruals..."*
2. **CFO/EBITDA** — Industry standard cash quality metric
3. **Accrual Ratio** — Richardson et al. (2005) JAR *"Accruals and the Prediction of Future Cash Flows"*
4. **CCS** — Direct cash conversion measure (CFO/PAT ratio)
5. **Depreciation Volatility** — Behavioral accounting metric for policy changes
6. **Cash Yield** — Capital efficiency benchmark (vs G-Sec/risk-free)
7. **FCFE** — Dividend sustainability test (Campbell & Hentges, 2013)

---

## 💡 Key Takeaways

**What this tool is:**
- ✅ Forensic analysis of earnings quality
- ✅ Accrual manipulation detection
- ✅ Cash conversion efficiency
- ✅ Accounting red flag identification

**What this tool is NOT:**
- ❌ Valuation (P/E, DCF, etc.)
- ❌ Growth trajectory prediction
- ❌ Market timing signal
- ❌ Stock recommendation (buy/sell)

**Best used for:**
- Pre-investment diligence
- Risk detection in client portfolios
- Due diligence on new public issuances
- Forensic accounting investigations
- Investor education

---

## 📞 Support

For issues or questions:
1. Check the `.env` configuration
2. Verify API key validity
3. Test with known tickers (RELIANCE, INFY)
4. Check Python dependencies: `pip install -r requirements.txt`

---

**Last Updated:** May 25, 2026  
**Module:** profit_quality_tool.py  
**Toolkit:** SoFi Forensic Analysis | AI Portfolio Analyser
