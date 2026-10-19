from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import os
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import lime
import lime.lime_tabular

app = FastAPI(title="Madushani XAI API", version="1.0.0")

# Allow React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
V2_DIR = os.path.join(OUTPUTS_DIR, "v2")
FIGURES_DIR = os.path.join(OUTPUTS_DIR, "figures")

# PNG figures from experiments/model_and_xai_comparison.py, under /api so the
# Vite dev proxy forwards them like every other API call.
app.mount("/api/figures", StaticFiles(directory=FIGURES_DIR, check_dir=False), name="figures")


def load_json(filename: str, directory: str = OUTPUTS_DIR, producer: str = "the corresponding notebook"):
    filepath = os.path.join(directory, filename)
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"{filename} not found. Please run {producer} first."
        )
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Live LIME explainer, loaded once at startup ────────────────────────────
# Reuses the exact same setup as notebooks/2_lime_anomaly_diagnosis.ipynb,
# so a live explanation for an arbitrary real historical date is computed the
# same way the 15 pre-built instances were, just on demand.

MODEL_PATH = os.path.join(OUTPUTS_DIR, "xgb_model.pkl")
DATASET_CANDIDATES = [
    os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "behaviour-intelligence", "data", "raw", "load_forecasting_dataset_corrected.csv")),
    os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "load_forecasting_dataset_corrected.csv")),
]
DATASET_PATH = next((p for p in DATASET_CANDIDATES if os.path.exists(p)), DATASET_CANDIDATES[0])

TARGET_COL = "Load Demand (kW)"
FEATURE_COLS = [
    "Temperature (°C)", "Humidity (%)", "Wind Speed (m/s)", "Rainfall (mm)",
    "Solar Irradiance (W/m²)", "GDP (LKR)", "Per Capita Energy Use (kWh)",
    "Electricity Price (LKR/kWh)", "Day of Week", "Hour of Day", "Month", "Public Event"
]
FEATURE_NAMES = [
    "Temperature", "Humidity", "Wind Speed", "Rainfall", "Solar Irradiance",
    "GDP", "Per Capita Energy Use", "Electricity Price",
    "Day of Week", "Hour of Day", "Month", "Public Event"
]

_live_model = None
_live_explainer = None
_live_df_clean = None
_live_thresholds = None


def _get_demand_level(value: float) -> str:
    p25, p75, p90 = _live_thresholds
    if value < p25:
        return "low"
    if value < p75:
        return "medium"
    if value < p90:
        return "high"
    return "peak"


def _predict_fn(X):
    df_pred = pd.DataFrame(X, columns=FEATURE_NAMES)
    return _live_model.predict(df_pred)


@app.on_event("startup")
def load_live_explainer():
    global _live_model, _live_explainer, _live_df_clean, _live_thresholds

    if not os.path.exists(MODEL_PATH) or not os.path.exists(DATASET_PATH):
        # Live explanations stay unavailable, the two pre-built endpoints
        # below still work off the notebook-generated JSON files.
        return

    _live_model = joblib.load(MODEL_PATH)

    df = pd.read_csv(DATASET_PATH)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values("Timestamp").reset_index(drop=True)

    Q1, Q3 = df[TARGET_COL].quantile(0.25), df[TARGET_COL].quantile(0.75)
    IQR = Q3 - Q1
    _live_df_clean = df[
        (df[TARGET_COL] >= Q1 - 1.5 * IQR) & (df[TARGET_COL] <= Q3 + 1.5 * IQR)
    ].copy().reset_index(drop=True)

    _live_thresholds = (
        _live_df_clean[TARGET_COL].quantile(0.25),
        _live_df_clean[TARGET_COL].quantile(0.75),
        _live_df_clean[TARGET_COL].quantile(0.90),
    )

    X_background = _live_df_clean.sample(2000, random_state=42)[FEATURE_COLS].copy()
    X_background.columns = FEATURE_NAMES

    _live_explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=X_background.values,
        feature_names=FEATURE_NAMES,
        mode="regression",
        random_state=42,
        verbose=False,
    )


@app.get("/")
def root():
    return {"message": "Madushani XAI API is running", "docs": "/docs"}


# ── Component 1: SHAP Temporal Drift ──────────────────────────────────────────
@app.get("/api/temporal-drift")
def get_temporal_drift():
    """
    Returns SHAP feature importance values per year (2020–2025, 2025 is
    Jan–May only), rankings, drift analysis, key insights, and the
    forecasting model comparison / XGBoost performance.
    Run notebook 1_shap_temporal_drift.ipynb first to generate the data.
    """
    return load_json("temporal_drift.json")


# ── Component 2: LIME Anomaly Diagnosis ───────────────────────────────────────
@app.get("/api/anomaly-diagnosis")
def get_anomaly_diagnosis():
    return load_json("anomaly_diagnosis.json")


# ── v2: model and XAI comparison evidence ────────────────────────────────────
# Static results from experiments/model_and_xai_comparison.py. The script only
# reads the dataset and xgb_model.pkl; it never retrains the deployed model.
V2_PRODUCER = "experiments/model_and_xai_comparison.py"


@app.get("/api/v2/model-comparison")
def get_model_comparison_v2():
    return load_json("model_comparison_v2.json", V2_DIR, V2_PRODUCER)


@app.get("/api/v2/xai-comparison")
def get_xai_comparison_v2():
    return load_json("xai_comparison.json", V2_DIR, V2_PRODUCER)


@app.get("/api/v2/temporal-drift")
def get_temporal_drift_v2():
    return load_json("temporal_drift_v2.json", V2_DIR, V2_PRODUCER)


# ── Live LIME explanation for an arbitrary real historical date ──────────────
# Used by the "Future Behaviour Prediction" flow in Thanujan's dashboard: a
# future date has no real feature data to explain, so that flow passes a real
# matched historical date instead (see behaviour-intelligence's
# behavior_prediction.py, matched_dates field). This computes a genuine LIME
# explanation for that real day on demand, rather than reusing one of the 15
# fixed sample instances.
@app.get("/api/explain-date")
def explain_date(date: str):
    if _live_model is None or _live_explainer is None:
        raise HTTPException(503, "Live explainer not available (model or dataset missing)")

    try:
        target_date = pd.to_datetime(date).date()
    except Exception:
        raise HTTPException(422, f"Invalid date: {date}")

    day_rows = _live_df_clean[_live_df_clean["Timestamp"].dt.date == target_date]
    if len(day_rows) == 0:
        raise HTTPException(404, f"No data found for {date} in the demand dataset")

    # The peak reading of the day is the most representative moment to
    # explain, it is what would have driven that day's behaviour label.
    row = day_rows.loc[day_rows[TARGET_COL].idxmax()]

    instance_vals = row[FEATURE_COLS].values.astype(float)
    actual = float(row[TARGET_COL])
    predicted = float(_live_model.predict(pd.DataFrame([instance_vals], columns=FEATURE_NAMES))[0])
    error_kw = round(predicted - actual, 4)
    error_pct = round(abs(error_kw / actual) * 100, 4) if actual != 0 else 0.0
    demand_level = _get_demand_level(actual)

    # The explainer, its LimeBase and its discretizer share one RandomState
    # that advances on every call. Re-seeding it in place makes the same date
    # always give the same explanation.
    _live_explainer.random_state.seed(42)
    exp = _live_explainer.explain_instance(
        data_row=instance_vals,
        predict_fn=_predict_fn,
        num_features=len(FEATURE_NAMES),
        num_samples=1000,
    )

    lime_r2 = round(float(exp.score), 4)
    intercept_raw = exp.intercept
    intercept = round(float(list(intercept_raw.values())[0] if isinstance(intercept_raw, dict) else intercept_raw), 4)

    # In regression mode LIME stores the real weights under key 1 and a negated
    # copy under key 0, so key 1 must be read explicitly. as_list() returns the
    # same weights in the same order, with the rule text (e.g. "Temperature > 29.29").
    raw_contribs = exp.local_exp[1]
    rules = {feat_idx: rule for (feat_idx, _), (rule, _) in zip(raw_contribs, exp.as_list(label=1))}
    contributions = [
        {
            "feature": FEATURE_NAMES[feat_idx],
            "rule": rules[feat_idx],
            "weight": round(float(weight), 4),
            "value": round(float(instance_vals[feat_idx]), 4),
        }
        for feat_idx, weight in sorted(raw_contribs, key=lambda x: abs(x[1]), reverse=True)
    ]
    local_pred = round(float(exp.local_pred[0]), 4)
    feature_values = {
        FEATURE_NAMES[j]: round(float(instance_vals[j]), 4) for j in range(len(FEATURE_NAMES))
    }

    return {
        "id": f"live-{date}",
        "timestamp": str(row["Timestamp"]),
        "actual": round(actual, 2),
        "predicted": round(predicted, 2),
        "error_kw": error_kw,
        "error_pct": error_pct,
        "demand_level": demand_level,
        "lime_r2": lime_r2,
        "intercept": intercept,
        "local_pred": local_pred,
        "contributions": contributions,
        "feature_values": feature_values,
        "source": "live",
        "matched_date": date,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
