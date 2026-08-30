"""Shared non-model API configuration.

Model metadata and artifact paths live exclusively in model_registry.py and
each package's production_config.json.
"""
import os
from pathlib import Path

BASE_DIR=Path(__file__).resolve().parents[2]
DATA_PATH=BASE_DIR/"data"/"electricity_demand_srilanka_fixed.csv"
LOOKBACK=96
TARGET_COL="Load Demand (kW)"
FEATURE_COLS=["Temperature (°C)","Humidity (%)","Wind Speed (m/s)","Rainfall (mm)",
 "Solar Irradiance (W/m²)","sin_hour","cos_hour","sin_dow","cos_dow","sin_month","cos_month",
 "is_weekend","year_norm","Public Event","Poya Day","load_lag_96","load_lag_192","load_lag_672",
 "load_mean_week","load_std_day"]
N_FEATURES=len(FEATURE_COLS)

API_TITLE="EDIS Load Forecasting API"
API_DESCRIPTION="Seven-model Sri Lanka electricity-demand forecasting service"
API_VERSION="3.0.0"
ALLOWED_ORIGINS=[value.strip() for value in os.getenv("ALLOWED_ORIGINS",
 "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000").split(",") if value.strip()]

# Interactive default: enough stochastic passes for a useful uncertainty estimate
# without making each dashboard forecast wait for 100 sequential model calls.
MC_SAMPLES_DEFAULT=5
Q_HAT=66.996826171875  # Compatibility health field; model-specific values are in the registry.
DATA_STALE_THRESHOLD_MINUTES=float(os.getenv("DATA_STALE_THRESHOLD_MINUTES","120"))
HISTORICAL_MAX_HOURS=168
SAFE_START_OFFSET=LOOKBACK+96*7*4
