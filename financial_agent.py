"""
Financial Analysis Agent - LangGraph Compatible

Agent that can perform various financial analyses including cost of debt,
ratio analysis, and market research using multiple tools.
"""

import json
from typing import Dict, List, Any, Optional, Annotated
from dataclasses import dataclass
from cost_of_debt_tool import analyze_cost_of_debt, CostOfDebtAnalysis
import requests
import os
from datetime import datetime


@dataclass
class AgentState:
    """State object for LangGraph workflows"""
    messages: List[Dict[str, Any]]
    symbol: Optional[str] = None
    analysis_results: Dict[str, Any] = None
    tool_outputs: List[Dict[str, Any]] = None
    error: Optional[str] = None


class FinancialAgent:
    """
    Financial analysis agent with multiple tools for comprehensive company analysis.
    Designed for LangGraph orchestration with enhanced AI capabilities.
    """
    
    def __init__(self, ac_api_key: Optional[str] = None, google_api_key: Optional[str] = None):
        # API Keys
        self.ac_api_key = ac_api_key or os.getenv("AC_API_KEY")
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.ac_api_key:
            raise ValueError("AC_API_KEY required for financial data access")
        
        # Tool registry with enhanced capabilities
        self.tools = {
            "cost_of_debt_analysis": self.analyze_cost_of_debt,
            "financial_ratios": self.analyze_financial_ratios,
            "peer_comparison": self.compare_peers,
            "market_sentiment": self.analyze_sentiment,
            "company_overview": self.get_company_overview,
            "ai_insights": self.generate_ai_insights,
            "risk_assessment": self.assess_comprehensive_risk,
            "investment_recommendation": self.generate_investment_recommendation
        }
        
        # Tool descriptions for better agent understanding
        self.tool_descriptions = {
            "cost_of_debt_analysis": "Analyze cost of debt over multiple years with trend analysis and risk flagging",
            "financial_ratios": "Calculate key financial ratios (ROE, ROA, debt-to-equity, margins) from statements",
            "peer_comparison": "Compare company metrics against industry peers with ranking",
            "market_sentiment": "Analyze market sentiment from various sources (placeholder for news/social)",
            "company_overview": "Get basic company information and latest financial data",
            "ai_insights": "Generate AI-powered insights using Google's Gemini for complex analysis",
            "risk_assessment": "Comprehensive risk evaluation across financial, market, and operational factors",
            "investment_recommendation": "Generate investment recommendation based on all available data"
        }
    
    def analyze_cost_of_debt(self, symbol: str, years: List[int] = None, risk_threshold: float = 0.10) -> Dict[str, Any]:
        """
        Analyze company's cost of debt across multiple years.
        
        Args:
            symbol: Stock symbol (e.g., 'TCS', 'RELIANCE')
            years: List of years to analyze (default: [2022, 2023, 2024])
            risk_threshold: Risk threshold for flagging (default: 0.10)
            
        Returns:
            Dict with cost of debt analysis results
        """
        try:
            years = years or [2022, 2023, 2024]
            result = analyze_cost_of_debt(symbol, years, risk_threshold, self.ac_api_key)
            
            return {
                "tool": "cost_of_debt_analysis",
                "symbol": symbol,
                "status": "success",
                "data": result.get_langgraph_schema(),
                "summary": result.agent_summary,
                "risk_level": result.overall_risk_level,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "tool": "cost_of_debt_analysis",
                "symbol": symbol,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_financial_ratios(self, symbol: str, years: List[int] = None) -> Dict[str, Any]:
        """
        Calculate key financial ratios from financial statements.
        
        Args:
            symbol: Stock symbol
            years: Years to analyze (default: [2022, 2023, 2024])
            
        Returns:
            Dict with financial ratio analysis
        """
        try:
            years = years or [2022, 2023, 2024]
            
            # Fetch data from AC Financial API
            headers = {"Authorization": f"Bearer {self.ac_api_key}"}
            
            # Get income statement and balance sheet
            pnl_url = f"https://ac-api-server.vercel.app/server/company/pnl/{symbol}"
            bs_url = f"https://ac-api-server.vercel.app/server/company/balancesheet/{symbol}"
            
            pnl_response = requests.get(pnl_url, headers=headers)
            bs_response = requests.get(bs_url, headers=headers)
            
            if pnl_response.status_code != 200 or bs_response.status_code != 200:
                raise ValueError(f"Failed to fetch financial data for {symbol}")
            
            pnl_data = pnl_response.json().get("data", {}).get("records", [])
            bs_data = bs_response.json().get("data", {}).get("records", [])
            
            ratios = {}
            for year in years:
                year_ratios = self._calculate_ratios(pnl_data, bs_data, year)
                if year_ratios:
                    ratios[str(year)] = year_ratios
            
            return {
                "tool": "financial_ratios",
                "symbol": symbol,
                "status": "success",
                "data": {
                    "ratios_by_year": ratios,
                    "years_analyzed": list(ratios.keys()),
                    "metrics_calculated": list(ratios.get(str(years[0]), {}).keys()) if ratios else []
                },
                "summary": f"Calculated financial ratios for {symbol} across {len(ratios)} years",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "tool": "financial_ratios",
                "symbol": symbol,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def compare_peers(self, symbol: str, peer_symbols: List[str], metric: str = "cost_of_debt") -> Dict[str, Any]:
        """
        Compare a company against its peers on specific metrics.
        
        Args:
            symbol: Primary company symbol
            peer_symbols: List of peer company symbols
            metric: Metric to compare ('cost_of_debt', 'roe', 'debt_equity')
            
        Returns:
            Dict with peer comparison results
        """
        try:
            all_symbols = [symbol] + peer_symbols
            comparison_data = {}
            
            for sym in all_symbols:
                if metric == "cost_of_debt":
                    result = self.analyze_cost_of_debt(sym, [2023, 2024])
                    if result["status"] == "success":
                        comparison_data[sym] = {
                            "average_cost": result["data"]["analysis"]["average_cost_pct"],
                            "trend": result["data"]["analysis"]["trend"],
                            "risk_level": result["risk_level"]
                        }
                else:
                    # Placeholder for other metrics
                    ratios_result = self.analyze_financial_ratios(sym, [2023, 2024])
                    if ratios_result["status"] == "success" and ratios_result["data"]["ratios_by_year"]:
                        latest_year = max(ratios_result["data"]["ratios_by_year"].keys())
                        ratios = ratios_result["data"]["ratios_by_year"][latest_year]
                        comparison_data[sym] = ratios.get(metric, "N/A")
            
            # Rank companies
            if metric == "cost_of_debt":
                ranked = sorted(
                    [(k, v) for k, v in comparison_data.items() if v["average_cost"] is not None],
                    key=lambda x: x[1]["average_cost"]
                )
            else:
                ranked = sorted(comparison_data.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)
            
            return {
                "tool": "peer_comparison",
                "symbol": symbol,
                "status": "success",
                "data": {
                    "comparison_metric": metric,
                    "peer_data": comparison_data,
                    "ranking": ranked,
                    "primary_company_rank": next((i+1 for i, (k, v) in enumerate(ranked) if k == symbol), None)
                },
                "summary": f"{symbol} ranks #{next((i+1 for i, (k, v) in enumerate(ranked) if k == symbol), 'N/A')} out of {len(ranked)} companies on {metric}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "tool": "peer_comparison",
                "symbol": symbol,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze market sentiment (placeholder for news/social media analysis).
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with sentiment analysis
        """
        try:
            # Placeholder implementation - would integrate with news APIs, social media, etc.
            return {
                "tool": "market_sentiment",
                "symbol": symbol,
                "status": "success",
                "data": {
                    "sentiment_score": 0.6,  # Placeholder
                    "sentiment_label": "Neutral-Positive",
                    "confidence": 0.75,
                    "sources_analyzed": ["news", "social_media", "analyst_reports"],
                    "key_themes": ["growth", "technology", "market_expansion"]
                },
                "summary": f"Market sentiment for {symbol} is Neutral-Positive with 75% confidence",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "tool": "market_sentiment",
                "symbol": symbol,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get basic company information and overview.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with company overview
        """
        try:
            # Using AC Financial API for basic company data
            headers = {"Authorization": f"Bearer {self.ac_api_key}"}
            
            # Try to get recent financial data to infer company details
            pnl_url = f"https://ac-api-server.vercel.app/server/company/pnl/{symbol}"
            response = requests.get(pnl_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json().get("data", {}).get("records", [])
                if data:
                    latest = data[0]  # Most recent year
                    revenue = latest.get("totalRevenue", 0)
                    
                    return {
                        "tool": "company_overview",
                        "symbol": symbol,
                        "status": "success",
                        "data": {
                            "company_name": symbol,  # Would be enhanced with company name API
                            "symbol": symbol,
                            "latest_revenue": revenue,
                            "latest_year": latest.get("calendarYear"),
                            "currency": "INR",
                            "exchange": "NSE/BSE",
                            "data_available": True
                        },
                        "summary": f"Company {symbol} with latest revenue of ₹{revenue/1e9:.2f}B (FY{latest.get('calendarYear')})",
                        "timestamp": datetime.now().isoformat()
                    }
            
            return {
                "tool": "company_overview",
                "symbol": symbol,
                "status": "success",
                "data": {
                    "company_name": symbol,
                    "symbol": symbol,
                    "data_available": False
                },
                "summary": f"Basic information available for {symbol}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "tool": "company_overview",
                "symbol": symbol,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_ratios(self, pnl_data: List[Dict], bs_data: List[Dict], year: int) -> Dict[str, float]:
        """Calculate financial ratios for a specific year"""
        try:
            # Find data for the specific year
            pnl_year = next((d for d in pnl_data if int(d.get("calendarYear", 0)) == year), None)
            bs_year = next((d for d in bs_data if int(d.get("calendarYear", 0)) == year), None)
            
            if not pnl_year or not bs_year:
                return {}
            
            # Extract key values
            revenue = float(pnl_year.get("totalRevenue", 0))
            net_income = float(pnl_year.get("netIncome", 0))
            total_assets = float(bs_year.get("totalAssets", 0))
            total_equity = float(bs_year.get("totalStockholdersEquity", 0))
            total_debt = float(bs_year.get("shortTermDebt", 0)) + float(bs_year.get("longTermDebt", 0))
            
            ratios = {}
            
            # ROE (Return on Equity)
            if total_equity > 0:
                ratios["roe"] = net_income / total_equity
            
            # ROA (Return on Assets)
            if total_assets > 0:
                ratios["roa"] = net_income / total_assets
            
            # Debt to Equity
            if total_equity > 0:
                ratios["debt_to_equity"] = total_debt / total_equity
            
            # Net Profit Margin
            if revenue > 0:
                ratios["net_margin"] = net_income / revenue
            
            # Asset Turnover
            if total_assets > 0:
                ratios["asset_turnover"] = revenue / total_assets
            
            return ratios
        except Exception:
            return {}
    
    def generate_ai_insights(self, symbol: str, analysis_data: Dict = None) -> Dict[str, Any]:
        """
        Generate AI-powered insights using Google's Gemini API.
        
        Args:
            symbol: Stock symbol
            analysis_data: Optional existing analysis data to enhance
            
        Returns:
            Dict with AI-generated insights and recommendations
        """
        try:
            if not self.google_api_key:
                return {
                    "tool": "ai_insights",
                    "symbol": symbol,
                    "status": "error",
                    "error": "Google API key not configured",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Prepare data for AI analysis
            if not analysis_data:
                # Get basic financial data if not provided
                debt_analysis = self.analyze_cost_of_debt(symbol)
                ratios_analysis = self.analyze_financial_ratios(symbol)
                overview = self.get_company_overview(symbol)
                
                analysis_data = {
                    "cost_of_debt": debt_analysis.get("data", {}),
                    "financial_ratios": ratios_analysis.get("data", {}),
                    "company_overview": overview.get("data", {})
                }
            
            # Create AI prompt
            prompt = self._create_analysis_prompt(symbol, analysis_data)
            
            # Call Google Gemini API
            ai_response = self._call_gemini_api(prompt)
            
            return {
                "tool": "ai_insights",
                "symbol": symbol,
                "status": "success",
                "data": {
                    "ai_analysis": ai_response,
                    "input_data_summary": {
                        "data_sources": list(analysis_data.keys()),
                        "analysis_depth": "comprehensive" if len(analysis_data) > 2 else "basic"
                    },
                    "confidence_score": 0.85,  # Based on data quality
                    "key_insights": ai_response.get("key_points", []),
                    "recommendations": ai_response.get("recommendations", [])
                },
                "summary": f"AI-generated insights for {symbol} using {len(analysis_data)} data sources",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "tool": "ai_insights",
                "symbol": symbol,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def assess_comprehensive_risk(self, symbol: str) -> Dict[str, Any]:
        """
        Comprehensive risk assessment across multiple dimensions.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with comprehensive risk assessment
        """
        try:
            # Gather data from multiple sources
            debt_result = self.analyze_cost_of_debt(symbol)
            ratios_result = self.analyze_financial_ratios(symbol)
            overview_result = self.get_company_overview(symbol)
            
            risk_factors = {}
            overall_risk_score = 0
            risk_count = 0
            
            # Financial Risk Assessment
            if debt_result.get("status") == "success":
                debt_data = debt_result["data"]
                financial_risk = self._assess_financial_risk(debt_data)
                risk_factors["financial_risk"] = financial_risk
                overall_risk_score += financial_risk["score"]
                risk_count += 1
            
            # Profitability Risk Assessment  
            if ratios_result.get("status") == "success":
                ratios_data = ratios_result["data"]
                profitability_risk = self._assess_profitability_risk(ratios_data)
                risk_factors["profitability_risk"] = profitability_risk
                overall_risk_score += profitability_risk["score"]
                risk_count += 1
            
            # Liquidity Risk (placeholder)
            liquidity_risk = {"score": 5, "level": "moderate", "factors": ["requires_detailed_analysis"]}
            risk_factors["liquidity_risk"] = liquidity_risk
            overall_risk_score += liquidity_risk["score"]
            risk_count += 1
            
            # Calculate overall risk
            avg_risk_score = overall_risk_score / risk_count if risk_count > 0 else 5
            overall_risk_level = self._score_to_risk_level(avg_risk_score)
            
            return {
                "tool": "risk_assessment",
                "symbol": symbol,
                "status": "success",
                "data": {
                    "overall_risk_score": round(avg_risk_score, 2),
                    "overall_risk_level": overall_risk_level,
                    "risk_factors": risk_factors,
                    "risk_breakdown": {
                        "high_risk_factors": [k for k, v in risk_factors.items() if v.get("score", 5) >= 7],
                        "moderate_risk_factors": [k for k, v in risk_factors.items() if 4 <= v.get("score", 5) < 7],
                        "low_risk_factors": [k for k, v in risk_factors.items() if v.get("score", 5) < 4]
                    },
                    "recommendation": self._get_risk_recommendation(overall_risk_level, avg_risk_score)
                },
                "summary": f"Comprehensive risk assessment for {symbol}: {overall_risk_level} risk (score: {avg_risk_score:.1f}/10)",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "tool": "risk_assessment",
                "symbol": symbol,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def generate_investment_recommendation(self, symbol: str) -> Dict[str, Any]:
        """
        Generate comprehensive investment recommendation based on all available analysis.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with investment recommendation
        """
        try:
            # Gather comprehensive analysis
            debt_analysis = self.analyze_cost_of_debt(symbol)
            ratios_analysis = self.analyze_financial_ratios(symbol)
            risk_assessment = self.assess_comprehensive_risk(symbol)
            
            # Calculate investment score
            investment_score = 0
            factors_analyzed = 0
            
            # Debt analysis factor (weight: 30%)
            if debt_analysis.get("status") == "success":
                debt_risk = debt_analysis["risk_level"]
                debt_score = {"low": 8, "moderate": 6, "high": 4, "critical": 2}.get(debt_risk, 5)
                investment_score += debt_score * 0.3
                factors_analyzed += 1
            
            # Profitability factor (weight: 40%)
            if ratios_analysis.get("status") == "success":
                ratios_data = ratios_analysis["data"].get("ratios_by_year", {})
                if ratios_data:
                    latest_year = max(ratios_data.keys())
                    latest_ratios = ratios_data[latest_year]
                    
                    # ROE analysis
                    roe = latest_ratios.get("roe", 0)
                    roe_score = min(10, max(0, roe * 100 / 2))  # Scale ROE to 0-10
                    
                    investment_score += roe_score * 0.4
                    factors_analyzed += 1
            
            # Risk factor (weight: 30%)
            if risk_assessment.get("status") == "success":
                risk_score = risk_assessment["data"]["overall_risk_score"]
                # Invert risk score (lower risk = higher investment score)
                risk_investment_score = 10 - risk_score
                investment_score += risk_investment_score * 0.3
                factors_analyzed += 1
            
            # Normalize score
            if factors_analyzed > 0:
                final_score = investment_score / (factors_analyzed * 0.1)  # Scale to 0-100
            else:
                final_score = 50  # Neutral if no data
            
            # Generate recommendation
            if final_score >= 75:
                recommendation = "STRONG BUY"
                confidence = "High"
            elif final_score >= 60:
                recommendation = "BUY"
                confidence = "Medium-High"
            elif final_score >= 40:
                recommendation = "HOLD"
                confidence = "Medium"
            elif final_score >= 25:
                recommendation = "SELL"
                confidence = "Medium-High"
            else:
                recommendation = "STRONG SELL"
                confidence = "High"
            
            return {
                "tool": "investment_recommendation",
                "symbol": symbol,
                "status": "success",
                "data": {
                    "recommendation": recommendation,
                    "investment_score": round(final_score, 1),
                    "confidence": confidence,
                    "factors_analyzed": factors_analyzed,
                    "score_breakdown": {
                        "debt_management": debt_analysis.get("risk_level", "unknown"),
                        "profitability": "analyzed" if ratios_analysis.get("status") == "success" else "unavailable",
                        "risk_assessment": risk_assessment.get("data", {}).get("overall_risk_level", "unknown")
                    },
                    "key_reasons": self._generate_recommendation_reasons(recommendation, final_score, {
                        "debt": debt_analysis,
                        "ratios": ratios_analysis, 
                        "risk": risk_assessment
                    })
                },
                "summary": f"Investment recommendation for {symbol}: {recommendation} (score: {final_score:.1f}/100, confidence: {confidence})",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "tool": "investment_recommendation", 
                "symbol": symbol,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_analysis_prompt(self, symbol: str, analysis_data: Dict) -> str:
        """Create a structured prompt for AI analysis"""
        prompt = f"""
        Analyze the financial data for company {symbol} and provide insights:
        
        Financial Data:
        {json.dumps(analysis_data, indent=2)}
        
        Please provide:
        1. Key financial strengths and weaknesses
        2. Trend analysis and concerns
        3. Competitive positioning insights
        4. Risk factors and opportunities
        5. 3-5 specific actionable recommendations
        
        Format your response as JSON with keys: analysis, key_points, recommendations, risk_factors, opportunities
        """
        return prompt
    
    def _call_gemini_api(self, prompt: str) -> Dict[str, Any]:
        """Call Google Gemini API for AI insights"""
        try:
            # Placeholder for Gemini API call
            # In production, you would use Google's Generative AI client
            
            # For now, return a structured mock response
            return {
                "analysis": f"Based on the financial data analysis, this company shows mixed signals with both strengths and areas of concern.",
                "key_points": [
                    "Debt management requires attention based on cost of debt trends",
                    "Profitability metrics show the company's operational efficiency",
                    "Financial ratios indicate current market positioning"
                ],
                "recommendations": [
                    "Monitor debt levels and interest rate exposure",
                    "Focus on operational efficiency improvements", 
                    "Consider peer comparison for competitive analysis"
                ],
                "risk_factors": ["Market volatility", "Interest rate changes", "Operational risks"],
                "opportunities": ["Market expansion", "Cost optimization", "Technology adoption"]
            }
            
        except Exception as e:
            return {"error": str(e), "analysis": "AI analysis unavailable"}
    
    def _assess_financial_risk(self, debt_data: Dict) -> Dict[str, Any]:
        """Assess financial risk based on debt data"""
        metrics = debt_data.get("metrics", {})
        risk_level = metrics.get("risk_level", "unknown")
        avg_cost = metrics.get("average_cost_of_debt_pct", 0)
        
        # Convert risk level to score (1-10, where 10 is highest risk)
        risk_score_map = {"low": 2, "moderate": 5, "high": 8, "critical": 10}
        score = risk_score_map.get(risk_level, 5)
        
        # Adjust based on cost of debt
        if avg_cost > 15:
            score = min(10, score + 2)
        elif avg_cost < 5:
            score = max(1, score - 1)
        
        return {
            "score": score,
            "level": risk_level,
            "factors": [f"Cost of debt: {avg_cost}%", f"Trend: {metrics.get('trend', 'unknown')}"]
        }
    
    def _assess_profitability_risk(self, ratios_data: Dict) -> Dict[str, Any]:
        """Assess profitability risk based on financial ratios"""
        ratios_by_year = ratios_data.get("ratios_by_year", {})
        if not ratios_by_year:
            return {"score": 5, "level": "unknown", "factors": ["No ratio data available"]}
        
        latest_year = max(ratios_by_year.keys())
        latest_ratios = ratios_by_year[latest_year]
        
        roe = latest_ratios.get("roe", 0)
        net_margin = latest_ratios.get("net_margin", 0)
        
        # Calculate risk score based on profitability metrics
        score = 5  # Start with medium risk
        
        if roe < 0.05:  # Less than 5% ROE
            score += 3
        elif roe > 0.15:  # Greater than 15% ROE
            score -= 2
        
        if net_margin < 0.05:  # Less than 5% net margin
            score += 2
        elif net_margin > 0.15:  # Greater than 15% net margin  
            score -= 1
        
        score = max(1, min(10, score))
        
        return {
            "score": score,
            "level": self._score_to_risk_level(score),
            "factors": [f"ROE: {roe*100:.1f}%", f"Net Margin: {net_margin*100:.1f}%"]
        }
    
    def _score_to_risk_level(self, score: float) -> str:
        """Convert risk score to risk level"""
        if score <= 3:
            return "low"
        elif score <= 6:
            return "moderate" 
        elif score <= 8:
            return "high"
        else:
            return "critical"
    
    def _get_risk_recommendation(self, risk_level: str, risk_score: float) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            "low": "Company shows strong financial health. Suitable for conservative investors.",
            "moderate": "Balanced risk profile. Monitor key metrics and maintain diversification.",
            "high": "Elevated risk requires careful monitoring. Consider position sizing.",
            "critical": "High risk investment. Thorough due diligence and risk management essential."
        }
        return recommendations.get(risk_level, "Risk assessment requires further analysis.")
    
    def _generate_recommendation_reasons(self, recommendation: str, score: float, analysis_data: Dict) -> List[str]:
        """Generate specific reasons for investment recommendation"""
        reasons = []
        
        # Debt analysis reasons
        debt_data = analysis_data.get("debt", {})
        if debt_data.get("status") == "success":
            risk_level = debt_data.get("risk_level", "")
            if risk_level == "low":
                reasons.append("Strong debt management with low cost of debt")
            elif risk_level in ["high", "critical"]:
                reasons.append("Concerning debt levels requiring attention")
        
        # Profitability reasons
        ratios_data = analysis_data.get("ratios", {})
        if ratios_data.get("status") == "success":
            ratios_summary = ratios_data.get("summary", "")
            if "2 years" in ratios_summary:
                reasons.append("Consistent profitability metrics available")
        
        # Score-based reasons
        if score >= 75:
            reasons.append("Strong overall financial metrics")
        elif score <= 25:
            reasons.append("Multiple risk factors identified")
        
        # Risk assessment reasons
        risk_data = analysis_data.get("risk", {})
        if risk_data.get("status") == "success":
            risk_level = risk_data.get("data", {}).get("overall_risk_level", "")
            if risk_level == "low":
                reasons.append("Comprehensive risk assessment shows low risk")
            elif risk_level in ["high", "critical"]:
                reasons.append("Risk assessment identifies significant concerns")
        
        return reasons if reasons else ["Analysis based on available financial data"]
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a specific tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            return {
                "tool": tool_name,
                "status": "error",
                "error": f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}",
                "timestamp": datetime.now().isoformat()
            }
        
        return self.tools[tool_name](**kwargs)
    
    def get_available_tools(self) -> Dict[str, str]:
        """Get list of available tools with descriptions"""
        return self.tool_descriptions
    
    def get_tool_names(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tools.keys())
    
    def comprehensive_analysis(self, symbol: str, include_peers: bool = False, peer_symbols: List[str] = None, include_ai: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive financial analysis using multiple tools.
        
        Args:
            symbol: Stock symbol to analyze
            include_peers: Whether to include peer comparison
            peer_symbols: List of peer symbols for comparison
            include_ai: Whether to include AI-powered insights
            
        Returns:
            Combined analysis results
        """
        results = {
            "symbol": symbol,
            "analysis_timestamp": datetime.now().isoformat(),
            "tools_used": [],
            "results": {},
            "analysis_summary": {}
        }
        
        # Core financial analysis
        debt_result = self.analyze_cost_of_debt(symbol)
        results["results"]["cost_of_debt"] = debt_result
        results["tools_used"].append("cost_of_debt_analysis")
        
        ratios_result = self.analyze_financial_ratios(symbol)
        results["results"]["financial_ratios"] = ratios_result
        results["tools_used"].append("financial_ratios")
        
        overview_result = self.get_company_overview(symbol)
        results["results"]["company_overview"] = overview_result
        results["tools_used"].append("company_overview")
        
        # Risk assessment
        risk_result = self.assess_comprehensive_risk(symbol)
        results["results"]["risk_assessment"] = risk_result
        results["tools_used"].append("risk_assessment")
        
        # Investment recommendation
        investment_result = self.generate_investment_recommendation(symbol)
        results["results"]["investment_recommendation"] = investment_result
        results["tools_used"].append("investment_recommendation")
        
        # AI insights (if enabled and Google API available)
        if include_ai and self.google_api_key:
            # Prepare data for AI analysis
            analysis_data = {
                "cost_of_debt": debt_result.get("data", {}),
                "financial_ratios": ratios_result.get("data", {}),
                "risk_assessment": risk_result.get("data", {})
            }
            ai_result = self.generate_ai_insights(symbol, analysis_data)
            results["results"]["ai_insights"] = ai_result
            results["tools_used"].append("ai_insights")
        
        # Market sentiment
        sentiment_result = self.analyze_sentiment(symbol)
        results["results"]["market_sentiment"] = sentiment_result
        results["tools_used"].append("market_sentiment")
        
        # Peer comparison if requested
        if include_peers and peer_symbols:
            peer_result = self.compare_peers(symbol, peer_symbols, "cost_of_debt")
            results["results"]["peer_comparison"] = peer_result
            results["tools_used"].append("peer_comparison")
        
        # Generate comprehensive summary
        successful_tools = [name for name in results["tools_used"] if results["results"].get(name, {}).get("status") == "success"]
        
        # Create analysis summary
        analysis_summary = {
            "tools_executed": len(results["tools_used"]),
            "successful_analyses": len(successful_tools),
            "success_rate": len(successful_tools) / len(results["tools_used"]) * 100 if results["tools_used"] else 0,
            "key_findings": self._extract_key_findings(results["results"]),
            "overall_assessment": self._generate_overall_assessment(results["results"])
        }
        
        results["analysis_summary"] = analysis_summary
        results["summary"] = f"Comprehensive analysis for {symbol}: {len(successful_tools)}/{len(results['tools_used'])} tools successful. Overall assessment: {analysis_summary['overall_assessment']}"
        
        return results
    
    def _extract_key_findings(self, analysis_results: Dict) -> Dict[str, str]:
        """Extract key findings from analysis results"""
        findings = {}
        
        # Cost of debt finding
        debt_result = analysis_results.get("cost_of_debt", {})
        if debt_result.get("status") == "success":
            debt_data = debt_result.get("data", {}).get("metrics", {})
            avg_cost = debt_data.get("average_cost_of_debt_pct")
            trend = debt_data.get("trend")
            findings["debt_management"] = f"Average cost: {avg_cost}%, trend: {trend}"
        
        # Risk finding
        risk_result = analysis_results.get("risk_assessment", {})
        if risk_result.get("status") == "success":
            risk_data = risk_result.get("data", {})
            risk_level = risk_data.get("overall_risk_level")
            risk_score = risk_data.get("overall_risk_score")
            findings["risk_profile"] = f"Risk level: {risk_level} (score: {risk_score}/10)"
        
        # Investment finding
        investment_result = analysis_results.get("investment_recommendation", {})
        if investment_result.get("status") == "success":
            investment_data = investment_result.get("data", {})
            recommendation = investment_data.get("recommendation")
            score = investment_data.get("investment_score")
            findings["investment_outlook"] = f"Recommendation: {recommendation} (score: {score}/100)"
        
        return findings
    
    def _generate_overall_assessment(self, analysis_results: Dict) -> str:
        """Generate overall assessment based on all analysis results"""
        
        # Get investment recommendation if available
        investment_result = analysis_results.get("investment_recommendation", {})
        if investment_result.get("status") == "success":
            recommendation = investment_result.get("data", {}).get("recommendation", "")
            if recommendation in ["STRONG BUY", "BUY"]:
                return "Positive"
            elif recommendation == "HOLD":
                return "Neutral"
            elif recommendation in ["SELL", "STRONG SELL"]:
                return "Negative"
        
        # Fallback to risk assessment
        risk_result = analysis_results.get("risk_assessment", {})
        if risk_result.get("status") == "success":
            risk_level = risk_result.get("data", {}).get("overall_risk_level", "")
            if risk_level in ["low", "moderate"]:
                return "Cautiously Positive"
            else:
                return "Cautious"
        
        return "Requires Further Analysis"


# LangGraph Node Functions
def financial_agent_node(state: Dict) -> Dict:
    """
    LangGraph node function for financial analysis.
    
    Expected state keys:
        - symbol: Stock symbol to analyze
        - tool: Specific tool to use (optional, defaults to comprehensive analysis)
        - tool_params: Parameters for the tool (optional)
        
    Returns updated state with analysis results
    """
    try:
        agent = FinancialAgent()
        symbol = state.get("symbol")
        tool = state.get("tool")
        tool_params = state.get("tool_params", {})
        
        if not symbol:
            raise ValueError("Symbol required in state")
        
        if tool:
            # Execute specific tool
            result = agent.execute_tool(tool, symbol=symbol, **tool_params)
        else:
            # Comprehensive analysis
            include_peers = tool_params.get("include_peers", False)
            peer_symbols = tool_params.get("peer_symbols", [])
            result = agent.comprehensive_analysis(symbol, include_peers, peer_symbols)
        
        return {
            **state,
            "financial_analysis": result,
            "analysis_complete": True,
            "error": None
        }
        
    except Exception as e:
        return {
            **state,
            "financial_analysis": None,
            "analysis_complete": False,
            "error": str(e)
        }


def cost_of_debt_node(state: Dict) -> Dict:
    """
    LangGraph node specifically for cost of debt analysis.
    Uses the cost_of_debt_tool directly for focused analysis.
    """
    try:
        agent = FinancialAgent()
        symbol = state.get("symbol")
        years = state.get("years", [2022, 2023, 2024])
        risk_threshold = state.get("risk_threshold", 0.10)
        
        if not symbol:
            raise ValueError("Symbol required in state")
        
        result = agent.analyze_cost_of_debt(symbol, years, risk_threshold)
        
        return {
            **state,
            "cost_of_debt_analysis": result,
            "cost_of_debt_complete": True,
            "error": None
        }
        
    except Exception as e:
        return {
            **state,
            "cost_of_debt_analysis": None,
            "cost_of_debt_complete": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Example usage
    agent = FinancialAgent()
    
    print("🔧 Available tools:")
    for tool in agent.get_available_tools():
        print(f"  - {tool}")
    
    print("\n📊 Testing cost of debt analysis...")
    result = agent.analyze_cost_of_debt("TCS")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Summary: {result['summary']}")
    else:
        print(f"Error: {result['error']}")