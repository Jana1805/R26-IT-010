from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import joblib
import json
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Any

app = FastAPI(title="Electricity Demand Forecasting API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")

# Load model and features
try:
    model = joblib.load(os.path.join(SAVED_MODELS_DIR, "forecast_model.pkl"))
    with open(os.path.join(SAVED_MODELS_DIR, "model_metadata.json"), "r") as f:
        model_data = json.load(f)
    features = model_data["feature_names"]
    target = model_data["target_column"]
    with open(os.path.join(SAVED_MODELS_DIR, "reference.json"), "r") as f:
        reference = json.load(f)
    print("Model loaded successfully")
except Exception as e:
    print(f"Model loading failed: {e}")
    model = None

# Track predictions for dynamic metrics
prediction_history = []

@app.get("/")
def root():
    return {"message": "Electricity Demand Forecasting API", "status": "running"}

@app.get("/api/model-info")
def get_model_info():
    """Get model information and performance metrics"""
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Calculate dynamic metrics from prediction history
    dynamic_metrics = model_data.get("model_performance", {}).copy()
    if len(prediction_history) > 0:
        predictions = [p["prediction"] for p in prediction_history]
        if len(predictions) >= 2:
            # Calculate prediction variance and range
            pred_mean = np.mean(predictions)
            pred_std = np.std(predictions)
            pred_min = np.min(predictions)
            pred_max = np.max(predictions)
            
            dynamic_metrics.update({
                "recent_predictions": len(predictions),
                "prediction_mean": float(pred_mean),
                "prediction_std": float(pred_std),
                "prediction_range": {
                    "min": float(pred_min),
                    "max": float(pred_max),
                    "span": float(pred_max - pred_min)
                }
            })

    return {
        "model_type": model_data.get("model_type", "RandomForestRegressor"),
        "features": features,
        "target": target,
        "performance": dynamic_metrics,
        "status": "ready",
        "model_file": "forecast_model.pkl",
        "model_size_mb": round(os.path.getsize(os.path.join(SAVED_MODELS_DIR, "forecast_model.pkl")) / (1024*1024), 2),
        "feature_count": len(features),
        "training_samples": model_data.get("data_info", {}).get("train_samples", "Unknown"),
        "test_samples": model_data.get("data_info", {}).get("test_samples", "Unknown"),
        "total_samples": model_data.get("data_info", {}).get("total_samples", "Unknown"),
        "total_predictions_made": len(prediction_history),
        "model_comparison": model_data.get("model_comparison"),
        "feature_importances": model_data.get("feature_importances"),
        "stacking_ensemble": model_data.get("stacking_ensemble"),
        "deployment_decision": model_data.get("deployment_decision")
    }

def _clamp_nonneg(prediction: float) -> float:
    """Electricity demand can never be physically negative. The deployed
    stacking ensemble's meta-learner puts ~99.9% of its trust in the Linear
    Regression base learner (see model_metadata.json stacking_ensemble),
    which has no output floor, unlike Random Forest, tested inputs like
    Temperature=0C produce predictions around -1300 kW. Clamping here keeps
    the ensemble deployed as chosen while guaranteeing physically sane
    output.
    """
    return max(float(prediction), 0.0)


@app.post("/api/predict")
def predict_demand(input_data: Dict[str, Any]):
    """Make demand prediction with input features"""
    if not model:
        raise HTTPException(status_code=503, detail="Model not available")
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame([input_data])
        
        # Ensure all features are present
        for feature in features:
            if feature not in df.columns:
                df[feature] = 0  # Default value
        
        # Make prediction, clamped to a physically possible non-negative value
        prediction = _clamp_nonneg(model.predict(df[features])[0])

        # Track prediction for dynamic metrics
        prediction_record = {
            "prediction": float(prediction),
            "timestamp": pd.Timestamp.now().isoformat(),
            "input_features": input_data.copy()
        }
        prediction_history.append(prediction_record)
        
        # Keep only last 100 predictions to avoid memory issues
        if len(prediction_history) > 100:
            prediction_history.pop(0)
        
        return {
            "prediction": float(prediction),
            "unit": "kW",
            "input_features": input_data,
            "prediction_number": len(prediction_history)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {str(e)}")

@app.get("/api/scenarios")
def get_scenario_results():
    """Get scenario analysis results"""
    try:
        results_path = os.path.join(OUTPUTS_DIR, "scenario_results.json")
        if not os.path.exists(results_path):
            raise HTTPException(status_code=404, detail="Scenario analysis not found. Run notebook 2 first.")
        
        with open(results_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenarios: {str(e)}")

@app.post("/api/scenario-test")
def test_custom_scenario(scenario_data: Dict[str, Any]):
    """Test custom scenario with modified features"""
    if not model:
        raise HTTPException(status_code=503, detail="Model not available")
    
    try:
        # Get baseline input
        baseline_input = scenario_data.get("baseline", {})
        modifications = scenario_data.get("modifications", {})
        
        # Apply modifications
        test_input = baseline_input.copy()
        test_input.update(modifications)
        
        # Make predictions
        baseline_df = pd.DataFrame([baseline_input])
        test_df = pd.DataFrame([test_input])
        
        # Ensure all features
        for feature in features:
            if feature not in baseline_df.columns:
                baseline_df[feature] = 0
            if feature not in test_df.columns:
                test_df[feature] = 0
        
        baseline_pred = _clamp_nonneg(model.predict(baseline_df[features])[0])
        test_pred = _clamp_nonneg(model.predict(test_df[features])[0])
        
        change = test_pred - baseline_pred
        change_pct = (change / baseline_pred) * 100 if baseline_pred != 0 else 0
        
        return {
            "baseline_prediction": float(baseline_pred),
            "scenario_prediction": float(test_pred),
            "absolute_change": float(change),
            "percentage_change": float(change_pct),
            "unit": "kW"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scenario test failed: {str(e)}")

# ---------------------------------------------------------------------------
# Interactive "control room" endpoints
# ---------------------------------------------------------------------------
def _frame(overrides: Dict[str, Any], hours=None, extra=None) -> pd.DataFrame:
    """Typical-day inputs, overridden by the caller; one row per requested hour."""
    base = dict(reference["typical"])
    base.update({k: v for k, v in (overrides or {}).items() if k in features})
    if extra:
        base.update(extra)
    rows = []
    for h in (hours if hours is not None else [base["Hour of Day"]]):
        r = dict(base); r["Hour of Day"] = h; rows.append(r)
    return pd.DataFrame(rows)[features]


def _predict(overrides, hours=None, extra=None):
    return np.clip(model.predict(_frame(overrides, hours, extra)), 0, None)


@app.get("/api/reference")
def get_reference():
    """Feature ranges, a typical day, and a default supply limit for the UI."""
    if not model:
        raise HTTPException(status_code=503, detail="Model not available")
    return {**reference, "model_type": model_data.get("model_type"),
            "performance": model_data.get("model_performance"),
            "data_info": model_data.get("data_info")}


@app.post("/api/curve")
def demand_curve(body: Dict[str, Any]):
    """24-hour demand curve for a baseline and a what-if scenario in one call."""
    if not model:
        raise HTTPException(status_code=503, detail="Model not available")
    try:
        hours = list(range(24))
        base_in, scen_in = body.get("baseline", {}), body.get("scenario", {})
        merged = {**base_in, **scen_in}
        b, s = _predict(base_in, hours), _predict(merged, hours)
        def stats(a):
            return dict(peak=float(a.max()), peak_hour=int(a.argmax()), mean=float(a.mean()), total=float(a.sum() * 0.25 * 4))
        return {"hours": hours, "baseline": b.round(1).tolist(), "scenario": s.round(1).tolist(),
                "baseline_stats": stats(b), "scenario_stats": stats(s), "unit": "kW"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Curve failed: {e}")


@app.post("/api/explain")
def explain(body: Dict[str, Any]):
    """Why does demand look like this? One-factor-at-a-time attributions.

    change_drivers: how much each changed input moves demand away from the baseline.
    level_drivers:  how much each input moves this scenario's demand away from a typical day.
    """
    if not model:
        raise HTTPException(status_code=503, detail="Model not available")
    try:
        hour = int(body.get("hour", 19))
        base_in = {**body.get("baseline", {}), "Hour of Day": hour}
        scen_in = {**base_in, **body.get("scenario", {}), "Hour of Day": hour}
        typical = {**reference["typical"], "Hour of Day": hour}
        base_pred, scen_pred = float(_predict(base_in)[0]), float(_predict(scen_in)[0])
        full_base = {**typical, **base_in}
        full_scen = {**typical, **scen_in}

        change = []
        for f in features:
            if full_scen[f] != full_base[f]:
                d = float(_predict({**full_base, f: full_scen[f]})[0]) - base_pred
                change.append({"feature": f, "from": full_base[f], "to": full_scen[f], "effect_kw": d})
        interaction = (scen_pred - base_pred) - sum(c["effect_kw"] for c in change)

        typ_pred = float(_predict(typical)[0])
        level = []
        for f in features:
            if full_scen[f] != typical[f]:
                d = float(_predict({**typical, f: full_scen[f]})[0]) - typ_pred
                level.append({"feature": f, "value": full_scen[f], "typical": typical[f], "effect_kw": d})
        level.sort(key=lambda r: abs(r["effect_kw"]), reverse=True)
        change.sort(key=lambda r: abs(r["effect_kw"]), reverse=True)
        return {"hour": hour, "baseline_kw": base_pred, "scenario_kw": scen_pred, "typical_kw": typ_pred,
                "change_drivers": change, "interaction_kw": float(interaction), "level_drivers": level}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Explain failed: {e}")


SENSITIVITY_FEATURES = ["Temperature (°C)", "Humidity (%)", "Electricity Price (LKR/kWh)", "GDP (LKR)",
                        "Per Capita Energy Use (kWh)", "Rainfall (mm)", "Wind Speed (m/s)"]


@app.post("/api/sensitivity")
def sensitivity(body: Dict[str, Any]):
    """Tornado data: swing in demand when each factor goes from its low to high (5th-95th pct) value."""
    if not model:
        raise HTTPException(status_code=503, detail="Model not available")
    try:
        hour = int(body.get("hour", 19))
        cur = {**reference["typical"], **body.get("inputs", {}), "Hour of Day": hour}
        base = float(_predict(cur)[0]); out = []
        for f in SENSITIVITY_FEATURES:
            lo, hi = reference["ranges"][f]["p5"], reference["ranges"][f]["p95"]
            p_lo, p_hi = float(_predict({**cur, f: lo})[0]), float(_predict({**cur, f: hi})[0])
            out.append({"feature": f, "low": lo, "high": hi, "at_low_kw": p_lo, "at_high_kw": p_hi,
                        "swing_kw": abs(p_hi - p_lo)})
        out.sort(key=lambda r: r["swing_kw"], reverse=True)
        return {"hour": hour, "current_kw": base, "factors": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sensitivity failed: {e}")


import grid_lab
if model:
    grid_lab.register(app, model, features, reference, SAVED_MODELS_DIR)


@app.get("/api/health")
def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "endpoints": [
            "/api/model-info",
            "/api/predict",
            "/api/scenarios",
            "/api/scenario-test",
            "/api/reference",
            "/api/curve",
            "/api/explain",
            "/api/sensitivity",
            "/api/decision",
            "/api/recommend",
            "/api/live-weather",
            "/api/performance"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
