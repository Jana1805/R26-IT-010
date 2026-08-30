"""Final model registry and standardized inference endpoints."""
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from api.core import state
from api.core.model_registry import DEFAULT_MODEL_ID, REGISTRY
from api.services.model_service import ModelServiceError, model_service
from api.services.prediction_comparison import align_prediction_files, calculate_metrics

router=APIRouter(tags=["models"])
class PredictRequest(BaseModel):
    model_id:str|None=None
    values:list[list[float]]
    feature_names:list[str]|None=None
    forecast_timestamp:str
class CompareRequest(BaseModel):
    model_ids:list[str]=Field(default_factory=lambda:list(REGISTRY))
    values:list[list[float]]
    feature_names:list[str]|None=None
    forecast_timestamp:str

def _error(exc):
    status=404 if exc.code=="invalid_model_id" else 422 if exc.code.startswith("invalid_") or exc.code=="non_finite_input" else 503
    raise HTTPException(status_code=status,detail={"code":exc.code,"message":str(exc)})

@router.get("/api/models")
def models():
    return {"default_model_id":DEFAULT_MODEL_ID,"models":[spec.public_status() for spec in REGISTRY.values()]}

@router.get("/models")
def legacy_models():
    return {model_id:spec.display_name for model_id,spec in REGISTRY.items()}

@router.post("/api/predict")
def predict(request:PredictRequest):
    try: return model_service.predict(request.model_id,request.values,request.forecast_timestamp,request.feature_names)
    except ModelServiceError as exc: _error(exc)

@router.post("/api/compare")
def compare(request:CompareRequest):
    predictions=[]; errors=[]
    for model_id in request.model_ids:
        try: predictions.append(model_service.predict(model_id,request.values,request.forecast_timestamp,request.feature_names))
        except ModelServiceError as exc: errors.append({"model_id":model_id,"code":exc.code,"message":str(exc)})
    return {"forecast_timestamp":request.forecast_timestamp,"predictions":predictions,"errors":errors}

@router.get("/api/comparison")
def comparison(sample_limit:int=600):
    """Return recalculated, timestamp-aligned scientific comparison evidence."""
    sample_limit=max(100,min(sample_limit,1200))
    aligned,unavailable=align_prediction_files()
    if aligned.empty: raise HTTPException(503,"Aligned comparison data is unavailable")
    metrics=calculate_metrics(aligned)
    model_rows=[]
    for model_id,spec in REGISTRY.items():
        match=metrics[metrics.model_id==model_id]
        metric=None if match.empty else match.iloc[0].replace({np.nan:None}).to_dict()
        if metric:
            normal=aligned.actual_kw<aligned.actual_kw.quantile(.9)
            metric["normal_demand_MAE"]=float(np.mean(np.abs(aligned.loc[normal,"actual_kw"]-aligned.loc[normal,model_id])))
            metric["peak_MAE"]=metric.get("peak_top_10pct_MAE")
        model_rows.append({**spec.public_status(),"metrics":metric,
                           "comparison_status":"available" if metric else "unavailable",
                           "comparison_note":unavailable.get(model_id)})
    indices=np.linspace(0,len(aligned)-1,min(sample_limit,len(aligned)),dtype=int)
    sample=aligned.iloc[np.unique(indices)].copy(); sample["timestamp"]=sample.timestamp.astype(str)
    stats_path=Path(__file__).resolve().parents[2]/"outputs"/"final_model_comparison"/"statistical_comparison.csv"
    statistics=pd.read_csv(stats_path).replace({np.nan:None}).to_dict("records") if stats_path.is_file() else []
    return {"test_period":{"start":str(aligned.timestamp.iloc[0]),"end":str(aligned.timestamp.iloc[-1]),
                           "rows":len(aligned),"unit":"kW","sampled_rows":len(sample)},
            "models":model_rows,"aligned_sample":sample.replace({np.nan:None}).to_dict("records"),
            "statistical_tests":statistics,"methodology":"Metrics recalculated from identical aligned prediction rows."}

@router.get("/forecast")
def legacy_forecast(steps:int=24,n_passes:int|None=None,start_timestamp:str|None=None,
                    include_actuals:bool=True,model:str=DEFAULT_MODEL_ID):
    """Backward-compatible frontend adapter using the new service and response fields."""
    if state.RAW_DF is None: raise HTTPException(503,"Dataset is unavailable")
    try: spec=REGISTRY[model]
    except KeyError: raise HTTPException(404,"The requested model is not registered")
    if n_passes is not None and not 1 <= n_passes <= 100:
        raise HTTPException(422,"n_passes must be between 1 and 100")
    frame=state.RAW_DF
    anchor=pd.Timestamp(start_timestamp) if start_timestamp else frame.index[-1]
    pos=int(frame.index.searchsorted(anchor,side="right"))-1
    if pos+1<spec.lookback: raise HTTPException(400,"Not enough chronological history")
    results=[]
    # This adapter supports dataset-backed one-step windows without inventing future exogenous inputs.
    available=min(steps,len(frame)-pos-1)
    for offset in range(1,available+1):
        end=pos+offset
        window=frame.iloc[end-spec.lookback:end]
        try: result=model_service.predict(model,window.loc[:,spec.features].to_numpy(),frame.index[end],list(spec.features),mc_samples=n_passes)
        except ModelServiceError as exc: _error(exc)
        uncertainty=result["uncertainty"] or {}
        results.append({"timestamp":str(frame.index[end]),"hour":int(frame.index[end].hour),
          "forecast_kw":result["predicted_load_kw"],"lower_95_kw":uncertainty.get("lower_kw"),
          "upper_95_kw":uncertainty.get("upper_kw"),"mc_std_kw":uncertainty.get("predictive_std_kw"),
          "actual_kw":float(frame.iloc[end][spec.target_name]) if include_actuals else None})
    return {"model":spec.display_name,"model_id":spec.model_id,"steps":len(results),
      "n_mc_passes":(n_passes or spec.mc_samples) if spec.mc_dropout else 1,"q_hat_kw":spec.q_hat_kw or 0.0,
      "anchor_timestamp":str(frame.index[pos]),"window_mode":"selected_timestamp" if start_timestamp else "latest_data",
      "interval_note":"Validation-residual calibrated interval" if spec.q_hat_kw else "No scientifically defined interval",
      "supports_intervals":spec.q_hat_kw is not None,"comparison":{"actuals_available":len(results) if include_actuals else 0,"horizon_steps":len(results)},"forecasts":results}
