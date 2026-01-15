# AI Financial Analysis Agent

Comprehensive financial analysis system with agent-callable tools for LangGraph orchestration.

## 🚀 Features

### **Core Tools:**
- **Cost of Debt Analysis** - Multi-year debt cost analysis with trend detection
- **Financial Ratios** - ROE, ROA, debt-to-equity, profit margins calculation  
- **Peer Comparison** - Industry benchmarking and ranking
- **Risk Assessment** - Comprehensive multi-dimensional risk evaluation
- **Investment Recommendations** - AI-powered buy/sell recommendations
- **Market Sentiment** - Market analysis (extensible for news/social APIs)
- **AI Insights** - Google Gemini-powered financial analysis

### **Key Capabilities:**
- ✅ **AC Financial API Integration** (NSE/BSE Indian markets)
- ✅ **Google AI Integration** (Gemini API for insights)
- ✅ **LangGraph Workflow Ready** (Node functions included)
- ✅ **Comprehensive Risk Scoring** (0-10 scale across multiple factors)
- ✅ **Investment Scoring** (0-100 scale with confidence levels)
- ✅ **Multi-tool Orchestration** (8 specialized financial tools)

## 📊 Example Analysis Output

```
📈 TCS Analysis Results:
✅ Cost of Debt: 8.43% (stable, low risk)
✅ Risk Assessment: Moderate risk (4.0/10)
✅ Investment Recommendation: Based on comprehensive analysis
✅ Success Rate: 85.7% tool execution
```

## 🛠️ Setup

### **1. Clone Repository**
```bash
git clone https://github.com/SoFi-BITS/AI_Ki_MKC-Sofy.git
cd AI_Ki_MKC-Sofy
```

### **2. Environment Setup**
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install requests python-dotenv
```

### **3. API Configuration**
```bash
cp .env.example .env
# Edit .env with your API keys:
# AC_API_KEY="your_ac_financial_api_key"
# GOOGLE_API_KEY="your_google_api_key"
```

### **4. API Keys**
- **AC Financial API**: Get from https://ac-api-server.vercel.app
- **Google API**: Get from https://console.cloud.google.com

## 🚀 Usage

### **Direct Usage**
```python
from financial_agent import FinancialAgent

# Initialize agent
agent = FinancialAgent()

# Single tool analysis
debt_result = agent.analyze_cost_of_debt('TCS.NS', [2022, 2023, 2024])
risk_result = agent.assess_comprehensive_risk('TCS.NS')
investment_result = agent.generate_investment_recommendation('TCS.NS')

# Comprehensive analysis
full_analysis = agent.comprehensive_analysis(
    'RELIANCE.NS', 
    include_peers=True,
    peer_symbols=['TCS.NS', 'INFY.NS'],
    include_ai=True
)

print(f"Investment Recommendation: {full_analysis['results']['investment_recommendation']['data']['recommendation']}")
```

### **LangGraph Integration**
```python
from financial_agent import financial_agent_node, cost_of_debt_node

# Define workflow state
state = {
    "symbol": "TCS.NS",
    "tool": "comprehensive_analysis",
    "tool_params": {"include_ai": True}
}

# Execute in LangGraph workflow
updated_state = financial_agent_node(state)

# Or use specific analysis node
debt_state = {"symbol": "TCS.NS", "years": [2022, 2023, 2024]}
debt_result = cost_of_debt_node(debt_state)
```

## 🔧 Available Tools

| Tool | Description | Output |
|------|-------------|---------|
| `cost_of_debt_analysis` | Multi-year debt cost analysis | Cost %, trend, risk flags |
| `financial_ratios` | Key financial ratios calculation | ROE, ROA, margins, efficiency |
| `peer_comparison` | Industry benchmarking | Rankings, peer metrics |
| `risk_assessment` | Comprehensive risk evaluation | Risk score (0-10), factors |
| `investment_recommendation` | Buy/sell recommendations | Score (0-100), confidence |
| `market_sentiment` | Market analysis | Sentiment, themes, confidence |
| `company_overview` | Basic company data | Revenue, financials, metadata |
| `ai_insights` | Google AI-powered analysis | Insights, recommendations |

## 📈 Analysis Framework

### **Risk Assessment (0-10 scale)**
- **Financial Risk**: Debt management, cost trends
- **Profitability Risk**: ROE, margins, efficiency
- **Liquidity Risk**: Cash flow, working capital
- **Overall Risk**: Weighted composite score

### **Investment Scoring (0-100 scale)**
- **Debt Factor (30%)**: Cost of debt analysis
- **Profitability Factor (40%)**: ROE and efficiency metrics  
- **Risk Factor (30%)**: Comprehensive risk assessment
- **Final Recommendation**: STRONG BUY / BUY / HOLD / SELL / STRONG SELL

### **Symbol Format**
Use NSE format: `TCS.NS`, `RELIANCE.NS`, `INFY.NS`, etc.

## 🔒 Security

- ✅ API keys stored in `.env` (ignored by git)
- ✅ `.env.example` provides safe template
- ✅ No hardcoded credentials in code
- ✅ Environment-based configuration

## 🏗️ Architecture

```
financial_agent.py          # Main agent class with 8 tools
cost_of_debt_tool.py        # Specialized debt analysis tool  
.env                        # API keys (private)
.env.example               # Configuration template
README.md                  # This documentation
.gitignore                # Security protection
```

## 📊 Data Sources

- **AC Financial Data API**: Indian stock market data (NSE/BSE)
- **Google Gemini API**: AI-powered analysis and insights
- **Currency**: INR (Indian Rupees)
- **Coverage**: 3+ years historical data

## 🎯 LangGraph Workflows

The agent is designed for orchestration-based workflows:

```python
# Example workflow nodes
financial_agent_node(state)     # Comprehensive analysis
cost_of_debt_node(state)       # Focused debt analysis  

# State management
state = {
    "symbol": "company_symbol",
    "tool": "specific_tool_name", 
    "tool_params": {"param": "value"}
}
```

## 🚀 Production Ready

- ✅ **8 Financial Tools** operational
- ✅ **API Integration** working (AC Financial + Google)
- ✅ **Error Handling** comprehensive
- ✅ **LangGraph Compatible** with node functions
- ✅ **Extensible Architecture** for additional tools
- ✅ **Security Best Practices** implemented

**Built for professional financial analysis and AI agent orchestration.** 🎯
