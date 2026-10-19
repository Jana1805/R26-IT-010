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
    low_days: int
    detected_anomaly_days: int
    anomaly_days_labelled_peak: int
    anomaly_label_note: str
    cluster_interpretation: dict
    label_distribution: list
    risk_distribution: list
    recent_abnormal_days: list
    all_days: list


class PredictionResponse(BaseModel):
    predicted_label: str
    confidence_percent: float          # smoothed likelihood of predicted_label (same as likelihood_percent)
    likelihood_percent: float
    raw_frequency_percent: float       # share of matched days with predicted_label (unsmoothed)
    predicted_label_count: int
    risk_level: str
    matched_days_count: int
    match_strategy: str
    match_description: str
    label_counts: dict
    raw_probability_distribution: dict
    probability_distribution: dict     # Laplace-smoothed, sums to ~100
    smoothing: str
    explanation: str


class DayProfileResponse(BaseModel):
    date: str
    profile_points: list
    peak_demand: float
    mean_demand: float
    behavior_label: str
    behavior_risk_level: str
