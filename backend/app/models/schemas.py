from pydantic import BaseModel
from typing import Optional

class PredictionInput(BaseModel):
    temperature: float
    rainfall: float
    humidity: float
    wind_speed: Optional[float] = 0.0
    public_event: bool = False
    # Add other features as needed

class PredictionOutput(BaseModel):
    predicted_demand: float

class ScenarioInput(BaseModel):
    temperature_change: float = 0.0
    rainfall_change: float = 0.0
    public_event: bool = False
    # Baseline features
    baseline_temperature: float
    baseline_rainfall: float
    baseline_humidity: float
    baseline_wind_speed: Optional[float] = 0.0

class ScenarioOutput(BaseModel):
    baseline: float
    scenario: float
    change_percent: float
    risk: str