"""
AI Advisor service - integrates with Gemini/Grok API for intelligent decision support
"""
import json
from typing import Dict, List, Optional
from datetime import datetime
from app.config import get_settings

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class AIAdvisorService:
    """AI-powered energy planning advisor using Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI Advisor service
        
        Args:
            api_key: Google Gemini API key (or read from environment GEMINI_API_KEY)
        """
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        if self.api_key and genai is not None:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
        else:
            self.model = None
            print("WARNING: Gemini package/API key not available. Using fallback advisor.")
    
    def generate_analysis(self, scenario: Dict, prediction: Dict, risk_assessment: Dict) -> Dict:
        """
        Generate comprehensive AI analysis of the scenario
        
        Args:
            scenario: User scenario parameters
            prediction: Demand prediction results
            risk_assessment: Risk assessment results
        
        Returns:
            Dict with AI-generated analysis and recommendations
        """
        if self.model is None:
            return self._fallback_analysis(scenario, prediction, risk_assessment)
        
        # Prepare structured context for the LLM
        context = self._prepare_context(scenario, prediction, risk_assessment)
        
        # Generate prompt for Gemini
        prompt = self._create_advisor_prompt(context)
        
        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            # Parse response
            return self._parse_gemini_response(response.text, context)
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return self._fallback_analysis(scenario, prediction, risk_assessment)
    
    def _prepare_context(self, scenario: Dict, prediction: Dict, risk_assessment: Dict) -> Dict:
        """Prepare structured context for LLM"""
        return {
            'scenario': scenario,
            'prediction': prediction,
            'risk_assessment': risk_assessment,
            'timestamp': datetime.utcnow().isoformat(),
            'context_summary': self._generate_context_summary(scenario, prediction, risk_assessment)
        }
    
    def _generate_context_summary(self, scenario: Dict, prediction: Dict, risk_assessment: Dict) -> str:
        """Generate natural language summary of context for the LLM"""
        summary = f"""
SCENARIO ANALYSIS CONTEXT:

**Scenario Parameters:**
- Temperature Change: {scenario['temperature_change']}°C
- Industrial Load Change: {scenario['industrial_load_change']}%
- Holiday Type: {scenario['holiday_type']}
- Weather Condition: {scenario['weather_condition']}
- Renewable Energy: {scenario['renewable_energy_contribution']}%

**Demand Predictions:**
- Base Demand: {prediction['base_demand']} MW
- Adjusted Demand: {prediction['adjusted_demand']} MW
- Peak Demand: {prediction['peak_demand']} MW
- Confidence Score: {prediction['confidence_score']}%

**Risk Assessment:**
- Risk Score: {risk_assessment['risk_score']}/100
- Risk Category: {risk_assessment['risk_category']}
- Demand Spike Probability: {risk_assessment['demand_spike_probability']:.1%}
- Peak Threshold Crossing: {risk_assessment['peak_threshold_crossing']:.1%}
- Load Imbalance Risk: {risk_assessment['load_imbalance_risk']:.1%}
- Identified Risks: {', '.join(risk_assessment['risk_factors'])}
"""
        return summary
    
    def _create_advisor_prompt(self, context: Dict) -> str:
        """Create the prompt for Gemini API"""
        prompt = f"""You are an expert energy grid analyst and electricity demand forecasting specialist. 
Based on the scenario analysis below, provide comprehensive strategic advice for grid operations and planning.

{context['context_summary']}

Please provide analysis in this exact JSON format (no markdown, just valid JSON):
{{
  "analysis": "2-3 paragraph detailed analysis of the scenario, explaining the demand patterns, key drivers, and grid implications",
  "key_insights": ["insight 1", "insight 2", "insight 3", "insight 4"],
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
  "risk_mitigation_strategies": ["strategy 1", "strategy 2", "strategy 3"],
  "next_steps": "Specific actionable next steps for energy planners and grid operators"
}}

Focus on:
1. What the key demand drivers are in this scenario
2. Grid stability and reliability concerns
3. Renewable energy opportunities and challenges
4. Specific operational recommendations
5. Long-term planning implications

Be specific, data-driven, and actionable."""
        return prompt
    
    def _parse_gemini_response(self, response_text: str, context: Dict) -> Dict:
        """Parse JSON response from Gemini"""
        try:
            # Extract JSON from response
            # Gemini might wrap JSON in markdown code blocks
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)
                
                return {
                    'analysis': parsed.get('analysis', 'No analysis available'),
                    'key_insights': parsed.get('key_insights', []),
                    'recommendations': parsed.get('recommendations', []),
                    'risk_mitigation_strategies': parsed.get('risk_mitigation_strategies', []),
                    'next_steps': parsed.get('next_steps', 'See analysis above'),
                    'generated_at': datetime.utcnow().isoformat()
                }
        except json.JSONDecodeError:
            pass
        
        # Fallback if JSON parsing fails
        return self._fallback_analysis(
            context['scenario'],
            context['prediction'],
            context['risk_assessment']
        )
    
    def _fallback_analysis(self, scenario: Dict, prediction: Dict, risk_assessment: Dict) -> Dict:
        """
        Fallback analysis when API is unavailable
        Uses rule-based logic to generate reasonable recommendations
        """
        recommendations = []
        insights = []
        strategies = []
        
        # Temperature-based insights and recommendations
        if scenario['temperature_change'] > 5:
            insights.append("Significant temperature increase will substantially elevate cooling demand")
            recommendations.append("Increase air conditioning capacity allocation by 15-20%")
            strategies.append("Pre-cool buildings during off-peak hours to shift demand")
        elif scenario['temperature_change'] < -5:
            insights.append("Lower temperatures will increase heating requirements")
            recommendations.append("Prepare heating systems and ensure adequate natural gas supply")
            strategies.append("Implement demand response for non-essential heating loads")
        
        # Industrial load insights
        if scenario['industrial_load_change'] > 30:
            insights.append(f"Heavy industrial activity projected ({scenario['industrial_load_change']}% increase)")
            recommendations.append("Coordinate with major industrial consumers for voluntary demand reduction")
            strategies.append("Offer time-of-use pricing incentives to shift industrial production")
        
        # Risk-based recommendations
        if risk_assessment['risk_category'] == 'Critical':
            insights.append("Critical risk level - immediate action required")
            recommendations.append("Activate emergency response protocols and increase reserve capacity")
            strategies.append("Deploy all available generation resources and demand response programs")
        elif risk_assessment['risk_category'] == 'High':
            insights.append("High risk scenario - enhanced monitoring needed")
            recommendations.append("Increase operating reserves and prepare demand response activation")
            strategies.append("Monitor real-time demand and be ready to implement contingency measures")
        
        # Renewable energy insights
        if scenario['renewable_energy_contribution'] > 40:
            insights.append("High renewable energy contribution improves sustainability but adds variability")
            recommendations.append("Ensure adequate energy storage and fast-ramping generation capacity")
            strategies.append("Implement advanced forecasting for renewable generation variability")
        
        # Peak demand insights
        if prediction['peak_demand'] > 11500:
            insights.append(f"Peak demand projection is very high ({prediction['peak_demand']} MW)")
            recommendations.append("Maximize all available generation and prepare demand response")
            strategies.append("Implement real-time pricing to manage peak consumption")
        
        # Generic insights if none added
        if not insights:
            insights.append("Scenario within normal operational parameters")
            insights.append(f"Predicted demand of {prediction['adjusted_demand']} MW is manageable")
        
        if not recommendations:
            recommendations.append("Continue standard grid operations")
            recommendations.append("Monitor demand trends and adjust as needed")
        
        if not strategies:
            strategies.append("Maintain regular maintenance and equipment checks")
            strategies.append("Update demand forecasts with actual consumption data")
        
        analysis = f"""Based on the scenario analysis, the grid is expected to experience demand of {prediction['adjusted_demand']} MW with a peak of {prediction['peak_demand']} MW. 
The risk level is {risk_assessment['risk_category'].lower()}, indicating {self._risk_description(risk_assessment['risk_category'])}.
Key factors driving demand are the {scenario['temperature_change']}°C temperature change, {scenario['industrial_load_change']}% industrial load adjustment, 
and {scenario['weather_condition']} weather conditions. Renewable energy contribution of {scenario['renewable_energy_contribution']}% will help offset fossil fuel dependence."""
        
        return {
            'analysis': analysis,
            'key_insights': insights[:4],
            'recommendations': recommendations[:3],
            'risk_mitigation_strategies': strategies[:3],
            'next_steps': self._generate_next_steps(risk_assessment),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _risk_description(self, category: str) -> str:
        """Generate description of risk category"""
        descriptions = {
            'Critical': 'careful monitoring and proactive intervention are essential',
            'High': 'enhanced coordination and reserve capacity are necessary',
            'Medium': 'standard operations with monitoring are appropriate',
            'Low': 'standard operations are sufficient'
        }
        return descriptions.get(category, 'monitoring is recommended')
    
    def _generate_next_steps(self, risk_assessment: Dict) -> str:
        """Generate next steps based on risk level"""
        if risk_assessment['risk_category'] == 'Critical':
            return "1) Immediately activate emergency protocols, 2) Brief senior operations staff, 3) Deploy all reserve capacity, 4) Contact major industrial users for demand reduction agreements, 5) Prepare public communication about potential brownouts"
        elif risk_assessment['risk_category'] == 'High':
            return "1) Brief operations team on elevated risk, 2) Ensure all generation units are available, 3) Pre-stage demand response programs, 4) Coordinate with regional grid operators, 5) Update demand forecasts hourly"
        elif risk_assessment['risk_category'] == 'Medium':
            return "1) Monitor demand in real-time, 2) Maintain normal reserve margins, 3) Update forecasts every 4 hours, 4) Keep communication channels open with operators, 5) Document actual vs. predicted performance"
        else:
            return "1) Continue normal operations, 2) Update forecasts regularly, 3) Perform routine maintenance, 4) Review historical data for accuracy, 5) Plan for next scenario analysis"
    
    def compare_scenarios(self, baseline: Dict, modified: Dict) -> Dict:
        """
        Generate comparative analysis between two scenarios
        """
        if self.model is None:
            return self._fallback_comparison(baseline, modified)
        
        prompt = f"""You are an expert in electricity grid analysis. Compare these two electricity demand scenarios:

BASELINE SCENARIO:
- Demand Prediction: {baseline['prediction']['adjusted_demand']} MW (peak: {baseline['prediction']['peak_demand']} MW)
- Risk Level: {baseline['risk_assessment']['risk_category']}
- Temperature: {baseline['scenario']['temperature_change']}°C
- Industrial Load: {baseline['scenario']['industrial_load_change']}%
- Weather: {baseline['scenario']['weather_condition']}

MODIFIED SCENARIO:
- Demand Prediction: {modified['prediction']['adjusted_demand']} MW (peak: {modified['prediction']['peak_demand']} MW)
- Risk Level: {modified['risk_assessment']['risk_category']}
- Temperature: {modified['scenario']['temperature_change']}°C
- Industrial Load: {modified['scenario']['industrial_load_change']}%
- Weather: {modified['scenario']['weather_condition']}

Provide comparison in this JSON format:
{{
  "differences": {{"demand_change_mw": number, "peak_change_mw": number, "risk_change": "string"}},
  "recommendation": "Which scenario is better and why (2-3 sentences)",
  "tradeoffs": ["tradeoff 1", "tradeoff 2"]
}}"""
        
        try:
            response = self.model.generate_content(prompt)
            json_start = response.text.find('{')
            json_end = response.text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                return json.loads(response.text[json_start:json_end])
        except:
            pass
        
        return self._fallback_comparison(baseline, modified)
    
    def _fallback_comparison(self, baseline: Dict, modified: Dict) -> Dict:
        """Fallback scenario comparison"""
        demand_diff = modified['prediction']['adjusted_demand'] - baseline['prediction']['adjusted_demand']
        peak_diff = modified['prediction']['peak_demand'] - baseline['prediction']['peak_demand']
        
        if demand_diff < 0:
            recommendation = f"Modified scenario is preferable - it reduces demand by {abs(demand_diff):.0f} MW"
        elif demand_diff > 0:
            recommendation = f"Baseline scenario is preferable - modified increases demand by {demand_diff:.0f} MW"
        else:
            recommendation = "Scenarios have equivalent demand profiles"
        
        return {
            'differences': {
                'demand_change_mw': round(demand_diff, 1),
                'peak_change_mw': round(peak_diff, 1),
                'risk_change': f"{baseline['risk_assessment']['risk_category']} → {modified['risk_assessment']['risk_category']}"
            },
            'recommendation': recommendation,
            'tradeoffs': [
                f"Baseline: {baseline['scenario']['temperature_change']}°C temp, {baseline['scenario']['industrial_load_change']}% industrial",
                f"Modified: {modified['scenario']['temperature_change']}°C temp, {modified['scenario']['industrial_load_change']}% industrial"
            ]
        }
