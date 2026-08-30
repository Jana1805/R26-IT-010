"""Health, data, demand, and analysis endpoints."""

import os
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from api.core.config import (
    Q_HAT,
    MC_SAMPLES_DEFAULT,
    LOOKBACK,
    FEATURE_COLS,
    TARGET_COL,
    HISTORICAL_MAX_HOURS,
    SAFE_START_OFFSET,
)
from api.core import state
from api.core.model_registry import REGISTRY
from api.services.model_service import model_service
from api.schemas.response import (
    DataRangeResponse,
    DataSourceResponse,
    DemandHistoricalResponse,
    DemandLiveResponse,
    HeatmapResponse,
    HealthResponse,
    ModelMetricsResponse,
)

router = APIRouter(tags=["behaviour"])


@router.get("/health", response_model=HealthResponse)
def health():
    """Check API and component status."""
    has_data = state.RAW_DF is not None and len(state.RAW_DF) > 0
    compatible = [key for key, spec in REGISTRY.items() if spec.enabled]
    return {
        "status": "ok" if (compatible and has_data) else "degraded",
        "model_loaded": bool(compatible),
        "models_loaded": compatible,
        "scalers_loaded": bool(compatible),
        "load_errors": getattr(state, "LOAD_ERRORS", {}),
        "data_loaded": has_data,
        "rows": len(state.RAW_DF) if has_data else 0,
        "oldest_timestamp": str(state.RAW_DF.index[0]) if has_data else None,
        "latest_timestamp": str(state.RAW_DF.index[-1]) if has_data else None,
        "feature_cols": len(FEATURE_COLS),
        "scaler_expects": len(FEATURE_COLS),
        "feature_match": True,
        "q_hat_kw": Q_HAT,
        "mc_samples": MC_SAMPLES_DEFAULT,
        "lookback": LOOKBACK,
        "available_models": list(REGISTRY.keys()),
        "registry": [spec.public_status() for spec in REGISTRY.values()],
        "lazy_loaded_models": model_service.loaded_model_ids,
    }


@router.get("/data/range", response_model=DataRangeResponse)
def data_range():
    """Get dataset time range and safe forecast start."""
    state.require_data()
    safe_start_idx = min(SAFE_START_OFFSET, len(state.RAW_DF) - 1)
    return {
        "min_timestamp": str(state.RAW_DF.index[0]),
        "max_timestamp": str(state.RAW_DF.index[-1]),
        "valid_forecast_from": str(state.RAW_DF.index[safe_start_idx]),
        "rows": int(len(state.RAW_DF)),
        "interval_minutes": 15,
    }


@router.get("/data/source", response_model=DataSourceResponse)
def data_source():
    """Get data source metadata."""
    has_data = state.RAW_DF is not None and len(state.RAW_DF) > 0
    latest_ts = str(state.RAW_DF.index[-1]) if has_data else None
    data_age = None
    is_stale = None
    if latest_ts:
        delta_min = (pd.Timestamp.now() - state.RAW_DF.index[-1]).total_seconds() / 60.0
        data_age = round(float(delta_min), 2)
        is_stale = data_age > float(os.getenv("DATA_STALE_THRESHOLD_MINUTES", "120"))
    return {
        "provider_mode": "dataset_backed_demo",
        "description": "Static dataset (2022-2025) - no live stream",
        "latest_timestamp": latest_ts,
        "data_age_minutes": data_age,
        "is_data_stale": is_stale,
        "live_data_enabled": False,
    }


@router.get("/demand/live", response_model=DemandLiveResponse)
def demand_live():
    """Get latest recorded demand."""
    state.require_data()
    ts = state.RAW_DF.index[-1]
    return {
        "timestamp": str(ts),
        "demand_kw": round(float(state.RAW_DF[TARGET_COL].iloc[-1]), 2),
        "hour": int(ts.hour),
    }


@router.get("/demand/historical", response_model=DemandHistoricalResponse)
def demand_historical(
    hours: int = Query(default=24, ge=1, le=HISTORICAL_MAX_HOURS),
    end_timestamp: str | None = None,
):
    """Get historical demand data."""
    state.require_data()
    n = min(hours * 4, len(state.RAW_DF))

    if end_timestamp:
        try:
            req_ts = pd.Timestamp(end_timestamp)
        except Exception:
            raise HTTPException(400, "Invalid end_timestamp - use ISO format")
        end_pos = int(state.RAW_DF.index.searchsorted(req_ts, side="right")) - 1
        if end_pos < 0:
            raise HTTPException(400, "end_timestamp is before dataset start")
        start_pos = max(0, end_pos - n + 1)
        slice_df = state.RAW_DF[[TARGET_COL]].iloc[start_pos : end_pos + 1]
    else:
        slice_df = state.RAW_DF[[TARGET_COL]].iloc[-n:]

    return {
        "hours": hours,
        "points": len(slice_df),
        "data": [
            {
                "timestamp": str(ts),
                "hour": int(ts.hour),
                "actual_kw": round(float(v), 2),
            }
            for ts, v in zip(slice_df.index, slice_df[TARGET_COL])
        ],
    }


@router.get("/analysis/heatmap", response_model=HeatmapResponse)
def heatmap():
    """Get hourly x day-of-week heatmap of demand."""
    state.require_data()
    df = state.RAW_DF[[TARGET_COL]].copy()
    df["hour"] = df.index.hour
    df["dow"] = df.index.dayofweek

    pivot = df.groupby(["hour", "dow"])[TARGET_COL].mean().round(1)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    rows = []
    for h in range(24):
        row = {"hour": f"{h:02d}:00"}
        for d in range(7):
            try:
                row[days[d]] = float(pivot[(h, d)])
            except KeyError:
                row[days[d]] = 0.0
        rows.append(row)

    return {"data": rows, "days": days}


@router.get("/model/metrics", response_model=ModelMetricsResponse)
def model_metrics(model: str = Query(default="mc_dropout")):
    """Get model architecture, training, and performance metrics."""
    model={"mc_dropout":"cnn_lstm_mc","baseline":"cnn_lstm_b"}.get(model,model)
    if model not in REGISTRY: raise HTTPException(404,"Unknown model")
    spec=REGISTRY[model]; metrics={}
    metrics_path=Path(__file__).resolve().parents[2]/"outputs"/"final_model_comparison"/"metrics_and_ranking.csv"
    if metrics_path.is_file():
        rows=pd.read_csv(metrics_path); match=rows[rows.model_id==model]
        if not match.empty:
            row=match.iloc[0]; metrics={"Test":{key:float(row[key]) for key in ("MAE","RMSE","MAPE","R2")}}
    return {"model":spec.display_name,"architecture":{"lookback":spec.lookback,"horizon":spec.horizon,"features":len(spec.features)},
            "training":{"split":"80/10/10","history_available":False},"metrics":metrics,
            "uncertainty":{"intervals_enabled":spec.q_hat_kw is not None,"mc_samples":spec.mc_samples if spec.mc_dropout else 1,"q_hat_kw":spec.q_hat_kw}}


