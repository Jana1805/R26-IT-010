"""
Scenario and Prediction models for MongoDB
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ScenarioInput(BaseModel):
    """User-defined scenario parameters"""
    temperature_change: float = Field(..., description="Temperature change in °C (-10 to +10)")
    industrial_load_change: float = Field(..., description="Industrial load change in % (-50 to +100)")
    holiday_type: str = Field(..., description="holiday, weekend, or normal")
    weather_condition: str = Field(..., description="rainy, sunny, or extreme")
    renewable_energy_contribution: float = Field(..., description="Renewable energy % (0-100)")
    user_id: Optional[str] = None
    scenario_name: Optional[str] = "Unnamed Scenario"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DemandPrediction(BaseModel):
    """Predicted demand outputs"""
    base_demand: float = Field(..., description="Base demand in MW")
    adjusted_demand: float = Field(..., description="Adjusted demand with factors applied")
    peak_demand: float = Field(..., description="Peak demand in MW")
    demand_curve: List[float] = Field(..., description="Hourly demand forecast (24 hours)")
    load_distribution: dict = Field(..., description="Distribution of load across regions")
    confidence_score: float = Field(..., description="Confidence level (0-100)")
    factors_applied: dict = Field(..., description="Breakdown of applied factors")


class RiskAssessment(BaseModel):
    """Risk intelligence outputs"""
    risk_score: float = Field(..., ge=0, le=100, description="Overall risk score (0-100)")
    risk_category: str = Field(..., description="Low, Medium, High, or Critical")
    risk_factors: List[str] = Field(..., description="List of identified risk factors")
    demand_spike_probability: float = Field(..., ge=0, le=1, description="Probability of demand spike")
    peak_threshold_crossing: float = Field(..., ge=0, le=1, description="Probability of exceeding historical peak")
    load_imbalance_risk: float = Field(..., ge=0, le=1, description="Risk of regional load imbalance")
    recommendation: str = Field(..., description="Brief recommendation for grid operators")


class AIAdvisorResponse(BaseModel):
    """AI Advisor LLM response"""
    analysis: str = Field(..., description="Detailed AI analysis of scenario")
    key_insights: List[str] = Field(..., description="Key findings from analysis")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    risk_mitigation_strategies: List[str] = Field(..., description="Strategies to mitigate identified risks")
    next_steps: str = Field(..., description="Suggested next steps for energy planners")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ScenarioResponse(BaseModel):
    """Complete scenario analysis response"""
    scenario_id: str
    scenario_input: ScenarioInput
    prediction: DemandPrediction
    risk_assessment: RiskAssessment
    ai_advisor: AIAdvisorResponse
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScenarioComparison(BaseModel):
    """Scenario comparison data"""
    baseline_scenario: ScenarioResponse
    modified_scenario: ScenarioResponse
    ai_suggested_scenario: Optional[ScenarioResponse] = None
    differences: dict = Field(..., description="Key differences between scenarios")
    recommendation: str = Field(..., description="Which scenario to choose and why")
