"""Strict alignment and recalculation for saved finalized predictions."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from api.core.model_registry import REGISTRY

ALIASES={
 "timestamp":("timestamp","target_timestamp"),"actual_kw":("actual_kw","actual_kW","actual"),
 "predicted_kw":("predicted_kw","mc_mean_kW","predicted")}
def normalize_predictions(model_id:str,path:Path)->pd.DataFrame:
    raw=pd.read_csv(path); selected={}
    for canonical,names in ALIASES.items():
        match=next((x for x in names if x in raw.columns),None)
        if not match: raise ValueError(f"{model_id}: missing {canonical} column")
        selected[canonical]=raw[match]
    frame=pd.DataFrame(selected); frame["timestamp"]=pd.to_datetime(frame["timestamp"],errors="raise")
    for col in ("actual_kw","predicted_kw"): frame[col]=pd.to_numeric(frame[col],errors="raise")
    if frame.empty or frame.isna().any().any() or not np.isfinite(frame[["actual_kw","predicted_kw"]]).all().all(): raise ValueError(f"{model_id}: invalid prediction values")
    if frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing: raise ValueError(f"{model_id}: timestamps must be unique and chronological")
    frame["model_id"]=model_id; return frame
def align_prediction_files():
    frames={}; unavailable={}
    for model_id,spec in REGISTRY.items():
        if not spec.predictions or not spec.predictions.is_file(): unavailable[model_id]="Predictions CSV unavailable"; continue
        try: frames[model_id]=normalize_predictions(model_id,spec.predictions)
        except ValueError as exc: unavailable[model_id]=str(exc)
    if not frames: return pd.DataFrame(),unavailable
    reference_id=next(iter(frames)); ref=frames[reference_id]
    compatible={reference_id:ref}
    for model_id,frame in list(frames.items())[1:]:
        if len(frame)!=len(ref): unavailable[model_id]="Row count differs from aligned test set"; continue
        if not frame.timestamp.equals(ref.timestamp): unavailable[model_id]="Timestamp order/test period differs"; continue
        if not np.allclose(frame.actual_kw,ref.actual_kw,rtol=0,atol=1e-5): unavailable[model_id]="Actual target values differ"; continue
        compatible[model_id]=frame
    aligned=ref[["timestamp","actual_kw"]].copy()
    for model_id,frame in compatible.items(): aligned[model_id]=frame.predicted_kw.to_numpy()
    return aligned,unavailable
def calculate_metrics(aligned:pd.DataFrame)->pd.DataFrame:
    rows=[]; actual=aligned.actual_kw.to_numpy()
    for model_id in [c for c in aligned if c not in ("timestamp","actual_kw")]:
        pred=aligned[model_id].to_numpy(); residual=actual-pred; nonzero=np.abs(actual)>np.finfo(float).eps
        rows.append({"model_id":model_id,"prediction_type":"mc_predictive_mean" if REGISTRY[model_id].mc_dropout else "deterministic",
          "rows":len(actual),"MAE":mean_absolute_error(actual,pred),"RMSE":mean_squared_error(actual,pred)**.5,
          "MAPE":np.mean(np.abs(residual[nonzero]/actual[nonzero]))*100,"R2":r2_score(actual,pred),
          "peak_top_10pct_MAE":mean_absolute_error(actual[actual>=np.quantile(actual,.9)],pred[actual>=np.quantile(actual,.9)])})
    result=pd.DataFrame(rows).sort_values(["MAE","RMSE"]); result.insert(0,"rank",range(1,len(result)+1)); return result
