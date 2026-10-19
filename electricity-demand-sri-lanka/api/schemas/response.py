"""
schemas/response.py — Response Models (Pydantic)
================================================
Type-safe response schemas for all API endpoints.
Auto-generates OpenAPI/Swagger docs.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# HEALTH & STATUS
# ─────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    """GET /health response."""
    status: str = Field(..., description="'ok' or 'degraded'")
    model_loaded: bool
    models_loaded: List[str] = Field(default_factory=list)
    available_models: List[str] = Field(default_factory=list)
    scalers_loaded: bool
    data_loaded: bool
    rows: int = Field(..., description="Number of rows in dataset")
    oldest_timestamp: Optional[str]
    latest_timestamp: Optional[str]
    feature_cols: int
    scaler_expects: int
    feature_match: Optional[bool]
    q_hat_kw: float
    mc_samples: int
    lookback: int
    load_errors: Dict[str, Any] = Field(default_factory=dict)
    registry: List[Dict[str, Any]] = Field(default_factory=list)
    lazy_loaded_models: List[str] = Field(default_factory=list)


class DataRangeResponse(BaseModel):
    """GET /data/range response."""
    min_timestamp: str
    max_timestamp: str
    valid_forecast_from: str = Field(
        ..., description="Earliest safe timestamp for forecasting"
    )
    rows: int
    interval_minutes: int


class DataSourceResponse(BaseModel):
    """GET /data/source response."""
    provider_mode: str
    description: str
    latest_timestamp: Optional[str]
    data_age_minutes: Optional[float]
    is_data_stale: Optional[bool]
    live_data_enabled: bool


# ─────────────────────────────────────────────────────────────
# DEMAND
# ─────────────────────────────────────────────────────────────
class DemandLiveResponse(BaseModel):
    """GET /demand/live response."""
    timestamp: str
    demand_kw: float = Field(..., ge=0)
    hour: int = Field(..., ge=0, le=23)


class HistoricalDemandPoint(BaseModel):
    """Single historical datapoint."""
    timestamp: str
    hour: int = Field(..., ge=0, le=23)
    actual_kw: float = Field(..., ge=0)


class DemandHistoricalResponse(BaseModel):
    """GET /demand/historical response."""
    hours: int
    points: int = Field(..., description="Actual number of points returned")
    data: List[HistoricalDemandPoint]


# ─────────────────────────────────────────────────────────────
# FORECAST
# ─────────────────────────────────────────────────────────────
class ForecastPoint(BaseModel):
    """Single forecast step."""
    timestamp: str
    hour: int = Field(..., ge=0, le=23)
    forecast_kw: float = Field(..., ge=0)
    lower_95_kw: Optional[float] = Field(None, ge=0)
    upper_95_kw: Optional[float] = Field(None, ge=0)
    mc_std_kw: Optional[float] = Field(None, ge=0, description="Epistemic uncertainty")
    actual_kw: Optional[float] = Field(None, ge=0, description="If available")


class ForecastComparison(BaseModel):
    """Forecast vs actuals comparison metadata."""
    actuals_available: int = Field(..., description="Number of actual values found")
    horizon_steps: int


class ForecastResponse(BaseModel):
    """GET /forecast response."""
    model: str
    steps: int
    n_mc_passes: int
    q_hat_kw: float = Field(..., description="Conformal interval radius")
    anchor_timestamp: str = Field(..., description="Anchor point for forecast")
    window_mode: str = Field(
        ..., description="'selected_timestamp' or 'latest_data'"
    )
    interval_note: str
    supports_intervals: bool = Field(..., description="Whether confidence bands are shown")
    comparison: ForecastComparison
    forecasts: List[ForecastPoint]


# ─────────────────────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────────────────────
class HeatmapRow(BaseModel):
    """Single row in heatmap (hour × day-of-week grid)."""
    hour: str = Field(..., example="00:00")
    Mon: float
    Tue: float
    Wed: float
    Thu: float
    Fri: float
    Sat: float
    Sun: float


class HeatmapResponse(BaseModel):
    """GET /analysis/heatmap response."""
    data: List[HeatmapRow]
    days: List[str] = Field(default=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])


# ─────────────────────────────────────────────────────────────
# MODEL METRICS
# ─────────────────────────────────────────────────────────────
class ModelMetricsResponse(BaseModel):
    """GET /model/metrics response."""
    model: str
    architecture: Dict[str, Any]
    training: Dict[str, Any]
    metrics: Dict[str, Dict[str, float]]
    uncertainty: Dict[str, Any]


# ─────────────────────────────────────────────────────────────
# SCENARIO ANALYSIS
# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# ERROR
# ─────────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    status_code: int
