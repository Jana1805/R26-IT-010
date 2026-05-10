from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str


class PipelineStepResponse(BaseModel):
    success: bool
    message: str
    data: dict


class DashboardSummaryResponse(BaseModel):
    total_days: int
    normal_days: int
    peak_days: int
    abnormal_days: int
    holiday_days: int
    label_distribution: list
    risk_distribution: list
    recent_abnormal_days: list
    all_days: list


class PredictionResponse(BaseModel):
    predicted_label: str
    confidence_percent: float
    risk_level: str
    matched_days_count: int
    match_strategy: str
    probability_distribution: dict
    explanation: str


class DayProfileResponse(BaseModel):
    date: str
    profile_points: list
    peak_demand: float
    mean_demand: float
    behavior_label: str
    behavior_risk_level: str
