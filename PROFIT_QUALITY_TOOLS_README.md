# Profit Quality & Accrual Analysis Tools — Detailed Calculation Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Fundamental Principles](#fundamental-principles)
3. [Tool 1: Cumulative PAT vs CFO](#tool-1-cumulative-pat-vs-cfo)
4. [Tool 2: CFO/EBITDA Consistency](#tool-2-cfoebitda-consistency)
5. [Tool 3: Accrual Profit Conversion](#tool-3-accrual-profit-conversion)
6. [Tool 4: Depreciation Volatility](#tool-4-depreciation-volatility)
7. [Tool 5: Cash Return vs Risk-Free](#tool-5-cash-return-vs-risk-free)
8. [Tool 6: FCFE Lumpiness](#tool-6-fcfe-lumpiness)
9. [Quick Reference Table](#quick-reference-table)
10. [Interpretation Guidelines](#interpretation-guidelines)

---

## Overview

The **Profit Quality & Accrual Analysis** toolkit provides 6 LangChain-compatible tools for forensic financial analysis of Indian stocks. The core principle: **High-quality earnings always convert to cash**. Accounting manipulation leaves detectable patterns.

**Module:** `profit_quality_tools.py`
**Input:** Indian stock ticker (NSE/BSE symbol)
**Output:** JSON with metrics, flags, and interpretation
**Monetary Unit:** ₹ Crores (Indian standard)

---

## Fundamental Principles

### 1. **Earnings ≠ Cash**

**Accounting Earnings (PAT)** = Net Income after all non-cash items (depreciation, accruals)
**Operating Cash Flow (CFO)** = Actual cash generated from operations

**Example:**
```
Company reports PAT: ₹1,000 Cr (revenue growth looks great!)
But CFO: ₹600 Cr (only 60% converts to cash)

Why the gap?
- ₹200 Cr: Receivables increase (credited but not collected)
- ₹150 Cr: Inventory buildup (paid cash upfront)
- ₹50 Cr: Timing differences
```

**Implication:** If PAT >> CFO consistently, earnings quality is questionable.

### 2. **Manipulators Exploit Accruals**

**Accruals** = Non-cash profit items
```
Total Accruals = (Client Receivables ↑) + (Inventory ↑) + (Deferred Revenue ↑) - (Cash ↑)
```

**Legitimate accruals** (one-time): Channel expansion, capex cycle
**Red flag accruals** (recurring): Growing receivables without revenue justification, inventory bloat

### 3. **Consistency = Quality**

Stable financial metrics = Predictable business = Lower manipulation risk
Volatile metrics = Accounting changes / one-offs / risks

---

## Tool 1: Cumulative PAT vs CFO

### Purpose
Detect **earnings divergence**: When reported profit significantly exceeds actual cash generation over a decade.

### Calculation

#### Step 1: Fetch Data
```
Fetch 10 years of annual data for ticker
Extract: PAT (Profit After Tax), CFO (Cash From Operations) for each year
```

#### Step 2: Cumulative 10-Year Analysis
```
Cumulative PAT (10Y)  = PAT₂014 + PAT₂015 + ... + PAT₂024
Cumulative CFO (10Y) = CFO₂014 + CFO₂015 + ... + CFO₂024

Divergence Ratio = Cumulative PAT / Cumulative CFO
```

**Example Calculation:**
```
Year    PAT (₹Cr)    CFO (₹Cr)
2015    800          750
2016    900          820
2017    1000         880
2018    1100         900
2019    1200         950
2020    1300         1000
2021    1400         1100
2022    1500         1150
2023    1600         1200
2024    1750         1300

Cumulative PAT (10Y)  = 11,550 ₹ Cr
Cumulative CFO (10Y) = 9,950 ₹ Cr

Divergence Ratio = 11,550 / 9,950 = 1.161 (11.6% divergence)
```

#### Step 3: Rolling 3-Year Analysis
For each 3-year window (ending in each year):
```
Rolling 3Y PAT & CFO for window [Year-2, Year-1, Year]
Calculate divergence ratio for that period
Track trend: Improving? Deteriorating?
```

**Example:**
```
Window ending 2024:
  Cumulative PAT (2022-2024): 1500 + 1600 + 1750 = 4850
  Cumulative CFO (2022-2024): 1150 + 1200 + 1300 = 3650
  Ratio: 4850 / 3650 = 1.329 ← WORSENING (higher divergence)

Window ending 2023:
  Cumulative PAT (2021-2023): 1400 + 1500 + 1600 = 4500
  Cumulative CFO (2021-2023): 1100 + 1150 + 1200 = 3450
  Ratio: 4500 / 3450 = 1.304 ← TREND: Deterioration
```

### Interpretation Table

| Divergence Ratio | Interpretation | Action |
|---|---|---|
| 0.8–1.0 | ✅ Perfect (CFO ≥ PAT) | High earnings quality |
| 1.0–1.2 | ✓ Good (small gap) | Normal business accruals |
| 1.2–1.5 | ⚠️ Concerning (20–50% divergence) | Investigate accrual sources |
| 1.5+ | 🚨 Critical (>50% divergence) | Strong manipulation signals |

### Thresholds & Logic

**Why divergence ratio > 1.2 is a red flag:**
- In a healthy business, every ₹1 of profit should generate ₹0.80–1.00 in cash
- If it's only ₹0.83 (ratio 1.2), it means 17% of profits are "stuck" in non-cash accruals
- **Possible causes:**
  - Revenue recognition in Q4 but cash collected in Q1 (legitimate timing)
  - Receivables growing faster than revenue (red flag for channel stuffing)
  - Inventory buildup without sales growth (red flag for demand weakness)
  - Deferred liabilities/revenue timing (usually okay)

**Why rolling 3-year:**
- Shows recent trend (last 3 years more relevant than historical)
- If rolling 3Y ratio > 10Y ratio: earnings quality deteriorating
- If rolling 3Y ratio < 10Y ratio: improving (better cash conversion recently)

---

## Tool 2: CFO/EBITDA Consistency

### Purpose
Measure **cash conversion efficiency**: What % of operating profit converts to actual cash?

### Calculation

#### Step 1: Annual Ratio Calculation
For each year:
```
CFO/EBITDA Ratio = Operating Cash Flow / EBITDA

Where:
  CFO       = Cash From Operations (cash statement)
  EBITDA    = Earnings Before Interest, Tax, Depreciation, Amortization
            ≈ Operating Profit (income statement)
```

**Example Year:**
```
Year 2024:
  EBITDA: ₹2,500 Cr
  CFO:    ₹1,900 Cr
  Ratio:  1,900 / 2,500 = 0.76 ✓ (76% of operating earnings = cash)
```

#### Step 2: Annual Analysis
```
For each year:
  Calculate CFO/EBITDA
  Determine if ≥ 0.7 (threshold) or < 0.7 (below threshold)
  Track: Years with ratio < 0.7
```

#### Step 3: Summary Statistics
```
Total Years Analyzed:  10
Consistent Years (≥ 0.7):  8
Below Threshold Years (< 0.7):  2
Percentage Consistent:  80%
```

### Interpretation Table

| Ratio | Meaning | Cash Conversion |
|---|---|---|
| ≥ 1.0 | Perfect | 100%+ of EBITDA → CFO (excess cash collection) |
| 0.8–1.0 | Very Good | 80–100% of EBITDA → CFO (minimal working capital drag) |
| 0.7–0.8 | Good | 70–80% of EBITDA → CFO (normal tax/timing impact) |
| 0.5–0.7 | Weak | 50–70% of EBITDA → CFO (working capital buildup concern) |
| < 0.5 | Poor | <50% of EBITDA → CFO (red flag: accrual or structural issue) |

### Thresholds & Logic

**Why 0.7 threshold:**
- **Tax impact:** EBITDA excludes taxes; CFO includes tax payment (naturally ~20–25% reduction)
- **Working capital:** Changes in receivables, payables, inventory (0–5% natural reduction)
- **Total natural drag:** ~30% → Expected ratio ≈ 0.70
- **Healthy = 0.70+:** Company converts most EBITDA to cash

**Flag Logic:**
```
IF number of years (< 0.7) ≤ 1:
  Status = CONSISTENT (one-off issue, likely tax/timing)
ELSE IF number of years (< 0.7) > 1:
  Status = CONCERNING (pattern: systemic cash conversion issue)
```

**Why EBITDA instead of PAT:**
- **EBITDA removes:**
  - Financing structure (interest) → different debt levels shouldn't affect ratio
  - Depreciation (non-cash) → different asset ages shouldn't affect ratio
  - Taxes (variable) → different tax jurisdictions/rates shouldn't affect ratio
- **Result:** Comparable across companies & time periods

---

## Tool 3: Accrual Profit Conversion

### Purpose
Quantify **non-cash profit portion** and **cash conversion efficiency**. High accruals = potential manipulation.

### Calculation

#### Step 1: Accrual Ratio (Simplified Balance Sheet Method)
```
Accrual Ratio = (PAT - CFO) / Total Assets

Where:
  PAT          = Net Profit After Tax
  CFO          = Operating Cash Flow
  PAT - CFO    = Accrual portion of earnings (non-cash)
  Total Assets = Denominator to normalize by company size
```

**Example:**
```
Year 2024:
  PAT:           ₹1,200 Cr
  CFO:           ₹1,000 Cr
  Accruals:      1,200 - 1,000 = ₹200 Cr (non-cash earnings)
  Total Assets:  ₹10,000 Cr
  Accrual Ratio: 200 / 10,000 = 0.02 = 2% ✓ HEALTHY
```

#### Step 2: Cash Conversion Score
```
Cash Conversion Score = CFO / PAT

Where:
  Ideal: 0.8–1.1 (Most profit converts to cash)
  Below 0.8: Working capital drag / timing mismatches
  Above 1.1: One-off cash collections / receivable factoring
```

**Example (same year):**
```
Cash Conversion Score = 1,000 / 1,200 = 0.833 ✓ GOOD
(83.3% of profit becomes cash, 16.7% stays as accruals)
```

#### Step 3: Yearly Metrics Table
```
Year    PAT    CFO    Accrual Ratio    Cash Conversion    Status
2020    800    750    1.0%             0.94               ✓
2021    900    820    1.1%             0.91               ✓
2022    1000   880    1.2%             0.88               ✓
2023    1100   900    1.8%             0.82               ✓
2024    1200   1000   2.0%             0.83               ✓
```

#### Step 4: Average Accrual Ratio
```
Average Accrual Ratio = Mean of all yearly accrual ratios

Example: (1.0 + 1.1 + 1.2 + 1.8 + 2.0) / 5 = 1.42%
```

### Interpretation Table

| Avg Accrual Ratio | Assessment | Risk Level |
|---|---|---|
| < 2% | High-quality earnings | ✅ Low |
| 2–5% | Normal accrual levels | ✓ Acceptable |
| 5–10% | Elevated accruals | ⚠️ Medium |
| > 10% | High-accrual risk | 🚨 High |

| Cash Conversion | Assessment | Implication |
|---|---|---|
| > 1.1 | Exceptional (>110%) | One-off high collections, or working capital release |
| 0.8–1.1 | Healthy | Normal operations, good quality |
| 0.5–0.8 | Weak | Significant WC drag, timing issues |
| < 0.5 | Poor | Severe accruals, manipulation risk |

### Thresholds & Logic

**Why accruals matter in forensics:**
```
Accruals = discretionary accounting items (most manipulation happens here)

Example manipulation path:
1. Recognize revenue early (inflates PAT)
2. Collect cash later (CFO lags)
3. Accrual builds up over years
4. Eventually forced to reverse (write-off)
```

**Example of red-flag accrual buildup:**
```
Year 1: PAT ₹100, CFO ₹90, Accrual Ratio 1.0%
Year 2: PAT ₹120, CFO ₹95, Accrual Ratio 2.1% ← Growing accruals
Year 3: PAT ₹150, CFO ₹100, Accrual Ratio 3.3% ← Still growing
Year 4: PAT ₹100, CFO ₹120, Accrual Ratio -2.0% ← Reversal! (discovery phase)
```

**Why 5% threshold:**
- Below 5% = mostly cash-based accounting
- 5–10% = some discretionary accruals (acceptable in seasonal businesses)
- Above 10% = heavy reliance on accruals (manipulation risk)

---

## Tool 4: Depreciation Volatility

### Purpose
Detect **accounting policy changes**: Sudden depreciation swings often preceded earnings shocks.

### Calculation

#### Step 1: Depreciation as % of Sales
For each year:
```
Depreciation % of Sales = (Depreciation / Sales) × 100

Where:
  Depreciation    = P&L depreciation charge (non-cash)
  Sales           = Total revenue
```

**Example:**
```
Year 2024:
  Depreciation: ₹500 Cr
  Sales:        ₹10,000 Cr
  Percent:      (500 / 10,000) × 100 = 5.0%
```

#### Step 2: Collect 10-Year Series
```
Year    Sales    Depreciation    Deprec % of Sales
2015    5000     200             4.0%
2016    6000     240             4.0%
2017    7000     280             4.0%
2018    8000     320             4.0%
2019    9000     500             5.6% ← Spike!
2020    9500     510             5.4%
2021    10000    520             5.2%
2022    10500    530             5.0%
2023    11000    550             5.0%
2024    12000    600             5.0%
```

#### Step 3: Calculate Coefficient of Variation (CV)
```
CV = Standard Deviation / Mean

Step 3a: Calculate mean
  Mean = (4.0 + 4.0 + 4.0 + 4.0 + 5.6 + 5.4 + 5.2 + 5.0 + 5.0 + 5.0) / 10
       = 46.2 / 10 = 4.62%

Step 3b: Calculate deviations from mean
  Year    Deprec%    Deviation    Deviation²
  2015    4.0        -0.62        0.384
  2016    4.0        -0.62        0.384
  2017    4.0        -0.62        0.384
  2018    4.0        -0.62        0.384
  2019    5.6        +0.98        0.960
  2020    5.4        +0.78        0.608
  2021    5.2        +0.58        0.336
  2022    5.0        +0.38        0.144
  2023    5.0        +0.38        0.144
  2024    5.0        +0.38        0.144

Step 3c: Calculate standard deviation
  Variance = Sum of Deviation² / Count
           = 3.928 / 10 = 0.3928
  Std Dev = √0.3928 = 0.626%

Step 3d: Calculate CV
  CV = 0.626 / 4.62 = 0.135 (13.5%)
```

### Interpretation Table

| CV Value | Volatility | Assessment | Action |
|---|---|---|---|
| < 0.15 (15%) | Very Stable | ✅ Consistent asset base | Normal operations |
| 0.15–0.30 | Stable | ✓ Acceptable variation | Monitor for trends |
| 0.30–0.50 | Moderate | ⚠️ Some volatility | Investigate spikes |
| > 0.50 | Volatile | 🚨 Highly erratic | Red flag: accounting changes |

### Thresholds & Logic

**Why sudden depreciation changes are red flags:**
```
Possible causes of depreciation spikes:

✓ Legitimate:
  - Major capex cycle completed (new depreciation base)
  - Asset impairment/write-off (one-time charge)
  - Policy change for better accuracy

✗ Red Flag:
  - Extending useful lives (inflates profits)
  - Changing depreciation methods (hiding deterioration)
  - Selective impairments (managing earnings)
```

**Example: Earnings manipulation via depreciation:**
```
Company A (Normal):
  Depreciation as % of sales: 5.0% every year
  CV = 0.08 (8.5%) → Stable, predictable

Company B (Manipulative):
  Year 1-3: Depreciation % = 3.0% (aggressive, short useful lives)
  Year 4-6: Depreciation % = 5.0% (extended useful lives → reported earnings ↑)
  Year 7-10: Depreciation % = 4.0% (normalized)
  CV = 0.28 (28%) → Clear accounting change
```

**Why CV instead of absolute values:**
- **Absolute depreciation** = hard to compare (large companies > small companies)
- **Depreciation % of sales** = normalized (comparable across sizes)
- **CV metric** = captures volatility independent of scale

---

## Tool 5: Cash Return vs Risk-Free

### Purpose
Assess **capital efficiency**: Is excess cash earning minimal returns (red flag for mismanagement)?

### Calculation

#### Step 1: Annual Cash Return Percentage
```
Cash Return % = (Interest Income / Cash Balance) × 100

Where:
  Interest Income = Income from cash & cash equivalents (P&L)
  Cash Balance    = End of year cash balance (B/S)
```

**Example Year:**
```
Year 2024:
  Cash Balance:      ₹500 Cr
  Interest Income:   ₹30 Cr
  Cash Return %:     (30 / 500) × 100 = 6.0%
```

#### Step 2: Compare to Risk-Free Rate
```
India's 10Y Government Security Yield = ~7.2% (risk-free rate)

Analysis:
  IF Cash Return % ≥ Risk-Free Rate → ✓ Efficient allocation
  IF Cash Return % < Risk-Free Rate → ⚠️ Below minimum threshold
```

**Example:**
```
Cash Return:      6.0%
Risk-Free Rate:   7.2%
Gap:              -1.2% (underperforming by 120 basis points)
Flag:             ⚠️ BELOW RISK-FREE
```

#### Step 3: Yearly Trend Analysis
```
Year    Cash(₹Cr)    Interest(₹Cr)    Return%    vs G-Sec    Status
2020    300          18                6.0%       vs 6.5%     ⚠️
2021    350          21                6.0%       vs 6.8%     ⚠️
2022    400          24                6.0%       vs 6.9%     ⚠️
2023    450          27                6.0%       vs 7.1%     ⚠️
2024    500          30                6.0%       vs 7.2%     ⚠️

Pattern: Consistently underperforming → 5/5 years below threshold
```

#### Step 4: Summary Count
```
Total Years:                    10
Years above Risk-Free Rate:     3
Years Below Risk-Free Rate:     7
Percentage Below:               70%
```

### Interpretation Table

| Analysis | Interpretation | Action |
|---|---|---|
| Consistently ≥ 7.2% | Efficient cash deployment | ✅ Good capital discipline |
| Mixed (some <7.2%) | Normal rate environment changes | ✓ Acceptable |
| Most/all < 7.2% | Poor treasury management | ⚠️ Potential misallocation |
| < 4% for multiple years | Cash hoarding / inefficiency | 🚨 Red flag |

### Thresholds & Logic

**Why risk-free rate benchmark:**
```
Cash Deployment Hierarchy:

Level 1 (Risk-Free): G-Sec 7.2% ← Minimum threshold
  └─ Company should at least match this

Level 2 (Low-Risk): Corp Bonds 8–9%
  └─ Better deployment than G-Sec

Level 3 (Growth): Investing in capex / M&A 10%+
  └─ Ideal long-term use of cash

Red Flag: Cash earning < 6% consistently
  ✗ Suggests: Excess hoarding, poor treasury, operational inefficiency
```

**Real-world example:**
```
Company XYZ sits on ₹1,000 Cr cash, earning 4% (₹40 Cr/year)
Could earn 7.2% in G-Sec (₹72 Cr/year)
Annual opportunity cost: ₹32 Cr
Over decade: ₹320+ Cr lost to shareholders

Reason for red flag:
 - Suggests management fear of deployment
 - Or: Poor capital allocation discipline
 - Or: Preparations for distress (hidden from public)
```

**Note on rate changes:**
- If market rates collapse (e.g., central bank cuts), lower returns acceptable
- Look for **relative performance**: Is company matching peer rates?
- If peers earning 6% and company earning 4%, that's the red flag

---

## Tool 6: FCFE Lumpiness

### Purpose
Assess **free cash flow to equity sustainability**: Can company sustain dividends/buybacks?

### Calculation

#### Step 1: Annual FCFE Calculation
```
FCFE = CFO − CapEx + Net Debt Issuance

Where:
  CFO                    = Operating Cash Flow
  CapEx                  = Capital Expenditures (capex)
  Net Debt Issuance      = (Equity Raised) − (Debt Repayment)
                         = New equity raised − Debt repaid
```

**Example Year:**
```
Year 2024:
  CFO (operating):       ₹1,200 Cr
  CapEx (reinvestment):  ₹(300) Cr
  Equity Raised:         ₹50 Cr
  Debt Repaid:           ₹(100) Cr
  Net Debt Is:           50 - 100 = ₹(50) Cr

  FCFE = 1,200 - 300 + (−50) = ₹850 Cr
  (Cash available to equity shareholders = ₹850 Cr)
```

#### Step 2: Collect 10-Year FCFE Series
```
Year    CFO     CapEx   Debt Net    FCFE
2015    800     (150)   (20)        630
2016    850     (160)   0           690
2017    900     (170)   10          740
2018    950     (180)   (30)        740
2019    1000    (200)   20          820
2020    950     (220)   (50)        680
2021    1100    (250)   30          880
2022    1200    (300)   (50)        850
2023    1300    (350)   50          1000
2024    1400    (400)   (100)       900

Total FCFE series: [630, 690, 740, 740, 820, 680, 880, 850, 1000, 900]
```

#### Step 3: Calculate Coefficient of Variation (CV)
```
CV = Standard Deviation / Mean

Step 3a: Calculate mean
  Mean FCFE = (630 + 690 + 740 + 740 + 820 + 680 + 880 + 850 + 1000 + 900) / 10
            = 8210 / 10 = ₹821 Cr

Step 3b: Calculate deviations from mean
  Year    FCFE    Deviation    Deviation²
  2015    630     -191         36,481
  2016    690     -131         17,161
  2017    740     -81          6,561
  2018    740     -81          6,561
  2019    820     -1           1
  2020    680     -141         19,881
  2021    880     +59          3,481
  2022    850     +29          841
  2023    1000    +179         32,041
  2024    900     +79          6,241
  
  Sum = 129,250

Step 3c: Calculate standard deviation
  Variance = 129,250 / 10 = 12,925
  Std Dev = √12,925 = ₹113.7 Cr

Step 3d: Calculate CV
  CV = 113.7 / 821 = 0.138 (13.8%)
```

#### Step 4: Interpret FCFE Pattern
```
Average FCFE:      ₹821 Cr/year
CV:                13.8% (stable)
Dividend Payout:   ₹500 Cr/year

Sustainability Check:
  Average FCFE (821) > Dividend (500) ✓ SUSTAINABLE
  Even in worst year (680): Still covers dividend ✓
  Trend: Improving (FCFE growing) ✓
```

### Interpretation Table

| CV Value | Volatility | Dividend Sustainability | Risk Assessment |
|---|---|---|---|
| < 0.20 (20%) | Very Stable | ✅ Highly Sustainable | Low risk |
| 0.20–0.35 | Stable | ✓ Sustainable (normal) | Low-Medium risk |
| 0.35–0.50 | Moderate | ⚠️ Cyclical (variable) | Medium risk |
| > 0.50 | Lumpy | 🚨 Unsustainable | High risk |

### Thresholds & Logic

**Why FCFE >= Dividend matters:**
```
Company allocates ₹500 Cr/year as dividend

Scenario A: Avg FCFE ₹900 Cr (CV 15%)
  ✓ Comfortable margin
  ✓ Even in bad years (700 Cr): Covers dividend
  ✓ Dividend sustainable

Scenario B: Avg FCFE ₹600 Cr (CV 40%)
  ⚠️ Tight: Dividend = 83% of average FCFE
  ⚠️ In bad years (350 Cr): Can't cover dividend
  ⚠️ Dividend at risk; may be cut if downturn

Scenario C: Avg FCFE ₹400 Cr (CV 60%)
  🚨 Unsustainable: Dividend = 125% of average FCFE
  🚨 Company depleting cash to pay dividend
  🚨 Dividend cut highly likely (investors beware)
```

**FCFE Components Breakdown:**

1. **CFO (Operating Cash):** Cash from day-to-day business
2. **−CapEx (Reinvestment):** Cash needed to maintain/grow assets
3. **+Net Debt:** Additional financing that boosts available cash
   - Positive = More debt/equity raised (boosts FCFE artificially)
   - Negative = Debt repayment/equity buyback (reduces FCFE)

**Red Flags:**
```
Red Flag 1: Negative FCFE
  Company spending more on capex than it earns from operations
  Indicator: Growth phase (acceptable) OR distress (concern)

Red Flag 2: FCFE << Dividend
  Dividend not covered by free cash
  Indicator: Cutting cash reserves OR unsustainable (watch for cut)

Red Flag 3: High CV (>0.50)
  FCFE highly erratic (boom/bust cycle)
  Indicator: Cyclical business (acceptable) OR earnings quality issue (concern)
  Action: Check if cycles align with industry or idiosyncratic
```

**Example of unsustainable dividend:**
```
Company history:
  Year 1: FCFE ₹1,000, Div ₹600 (60%) → Healthy
  Year 2: FCFE ₹800, Div ₹600 (75%) → Stretching
  Year 3: FCFE ₹500, Div ₹600 (120%) → Negative!
  Action: Company depletes ₹100 Cr cash to maintain dividend
  
Investor warning: Dividend likely cut in Year 4
```

---

## Quick Reference Table

| Tool | Input | Core Formula | Red Flag Threshold | Unit |
|---|---|---|---|---|
| **PAT vs CFO** | Ticker | Σ PAT / Σ CFO | > 1.2 | Ratio |
| **CFO/EBITDA** | Ticker | CFO / EBITDA | < 0.7 | Ratio |
| **Accrual Ratio** | Ticker | (PAT − CFO) / Assets | > 5% | % |
| **Deprec Volatility** | Ticker | StdDev / Mean (Deprec%) | CV > 0.30 | CV |
| **Cash Return** | Ticker | Interest / Cash × 100 | < 7.2% | % (vs G-Sec) |
| **FCFE Lumpiness** | Ticker | CFO − CapEx + NetDebt | CV > 0.50 | CV |

---

## Interpretation Guidelines

### How to Read the JSON Output

Each tool returns JSON with this structure:

```json
{
  "ticker": "RELIANCE",
  "metric": "Tool Name",
  "summary": {
    "key_metric": value,
    "flag": "✅ GOOD / ⚠️ CAUTION / 🚨 RED FLAG"
  },
  "yearly_analysis": [ ... ],
  "interpretation": "Text explanation"
}
```

### Decision Framework

**Step 1: Identify Flags**
```
✅ No flag   = Low risk, normal financials
⚠️ Caution   = Investigate further, not conclusive
🚨 Red Flag  = Strong signal of problem, prioritize
```

**Step 2: Triangulate Evidence**
```
Single red flag: Could be explained away (capex cycle, tax timing)
Multiple flags: Pattern emerging (accounting issues likely)
All 6 tools flag: Highly suspicious (strong manipulation signals)
```

**Step 3: Cross-Check with Qualitative**
```
Red flags + negative news/SEBI notices = Likely manipulation
Red flags + benign explanations = Could be false positive
```

### Common Scenarios

**Scenario A: High-Quality Business**
```
✅ PAT ≈ CFO (divergence < 1.1)
✓ CFO/EBITDA > 0.8
✓ Accrual ratio < 3%
✓ Depreciation stable (CV < 0.2)
✓ Cash earning ≥ 7%
✓ FCFE stable, dividend covered (CV < 0.3)

→ Conclusion: Legitimate earnings, low manipulation risk
```

**Scenario B: Accounting Concerns**
```
⚠️ Divergence ratio 1.3
⚠️ CFO/EBITDA below 0.6 for 2+ years
⚠️ Accrual ratio 8%
⚠️ Depreciation % jumped from 4% → 8%
⚠️ Cash earning 4% (vs 7% peers)
⚠️ FCFE lumpy (CV 0.45)

→ Conclusion: Multiple red flags, investigate receivables, inventory, and accounting policies
```

**Scenario C: Cyclical Business (Acceptable)**
```
Divergence ratio 1.15 (normal for cyclical)
CFO/EBITDA 0.65 (acceptable, capex-heavy year)
Accrual ratio ✓ (low)
Depreciation stable ✓
Cash return ✓ (market rates low, intentional)
FCFE lumpy (CV 0.55) → But negative only in growth years ✓

→ Conclusion: Expected volatility in cyclical industry, financials sound
```

---

## Frequently Asked Questions

### Q: Why is divergence ratio > 1.2 a red flag if even 1.0 is "perfect"?
**A:** In practice, no business is perfectly 1.0:
- Taxes reduce CFO vs PAT (natural)
- Working capital changes cause timing lags (normal)
- Expected ratio: 0.8–1.0 for cash-generating businesses
- If ratio > 1.2, it means CFO is significantly lower than PAT
- **Example:** If you report ₹100 profit but only get ₹83 in cash, where's the ₹17? (Accruals!)

### Q: How do I differentiate between legitimate and suspicious accruals?
**A:**
```
Legitimate accrual (one-time):
- New product launch → Inventory buildup → Sells off in next year
- Seasonal business → Receivables spike → Collected in next quarter
- Signal: High accrual in Y1, normalizes in Y2

Suspicious accrual (recurring):
- Receivables growing faster than revenue (underwritten sales? channel stuffing?)
- Inventory growing but sales flat (demand weakness hidden?)
- Deferred revenue declining (revenue recognition issue?)
- Signal: High accruals year after year, never normalizes
```

### Q: If a company has negative FCFE, does it mean dividend is unsustainable?
**A:** Not necessarily:
```
Scenario 1: Negative FCFE is temporary (growth capex phase)
- Company investing heavily for growth
- FCFE negative today, but will be positive tomorrow
- Dividend from cash reserves is okay (temporary)

Scenario 2: Negative FCFE is recurrent
- Company structurally not generating enough cash for capex + dividends
- Dividend is unsustainable
- Will likely be cut

Action: Check if capex is declining (scenario 1) or recurring (scenario 2)
```

### Q: Why use Coefficient of Variation instead of standard deviation?
**A:**
```
Standard Deviation alone:
- Abs StdDev: Hard to judge if ₹100 Cr volatility is "high"
- Dependent on scale (large company has larger StdDev)

Coefficient of Variation (StdDev/Mean):
- Normalized metric (comparable across companies)
- Dimensionless (pure percentage)
- CV 0.15 = 15% volatility (easy to benchmark)
- Industry comparable: If peers have CV 0.1, our CV 0.3 stands out
```

---

## Technical Notes

### Data Requirements
Each tool needs 10 years of annual data:
```
Required fields:
- year, pat (profit after tax), cfo (operating cash flow)
- ebitda, sales, depreciation
- cash (cash balance), interest_income, total_assets
- capex, equity_raised, debt_repayment, risk_free_rate
```

### Handling Missing Data
```
Strategy: Skip years with insufficient data, mark as "N/A"
Example: If interest_income missing → Cash Return tool returns "N/A" for that year
Never crash: One missing field doesn't break entire tool
```

### API Integration
Each tool fetches from: `{STOCK_API_BASE_URL}/financials/annual?ticker=TICKER&years=10`

Expected response format:
```json
{
  "years": [
    {"year": 2024, "pat": 1200, "cfo": 1000, "ebitda": 1800, ...},
    {"year": 2023, "pat": 1100, "cfo": 920, "ebitda": 1700, ...},
    ...
  ]
}
```

---

## References & Further Reading

**Financial Theory:**
- Sloan, R. (1996). "Do stock prices fully reflect information in accruals and cash flows about future earnings?" *The Accounting Review*
- Dechow, P., & Dichev, I. (2002). "The quality of accruals and earnings"

**Indian Context:**
- Accounting Standards: Ind-AS (Indian Modified Accounting Standards)
- G-Sec yields: RBI (Reserve Bank of India) publications
- Stock exchanges: NSE & BSE (National Stock Exchange & Bombay Stock Exchange)

**Tools & Language:**
- LangChain Documentation: https://python.langchain.com/
- Pydantic Validation: https://docs.pydantic.dev/
