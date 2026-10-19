"""Evidence-backed registry for the seven finalized forecasting packages."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

BASE_DIR=Path(__file__).resolve().parents[2]
MODELS_DIR=BASE_DIR/"models"
MODEL_IDS=("cnn","lstm","transformer","cnn_lstm_b","cnn_transformer_b","cnn_lstm_mc","cnn_transformer_mc")
DEFAULT_MODEL_ID="cnn_lstm_b"
PARAMETER_COUNTS={"cnn":206817,"lstm":129921,"transformer":155521,"cnn_lstm_b":146145,
                  "cnn_transformer_b":166369,"cnn_lstm_mc":146145,"cnn_transformer_mc":166369}

@dataclass(frozen=True)
class ModelSpec:
    model_id:str; display_name:str; artifact:Path; feature_scaler:Path; target_scaler:Path
    config:Path; predictions:Path|None; features:tuple[str,...]; lookback:int=96; horizon:int=1
    target_name:str="Load Demand (kW)"; target_unit:str="kW"; mc_dropout:bool=False
    mc_samples:int=1; q_hat_kw:float|None=None; custom_objects:tuple[str,...]=()
    @property
    def enabled(self): return all(p.is_file() for p in (self.artifact,self.feature_scaler,self.target_scaler,self.config))
    def public_status(self):
        missing=[name for name,path in (("artifact",self.artifact),("feature scaler",self.feature_scaler),("target scaler",self.target_scaler),("configuration",self.config)) if not path.is_file()]
        return {"model_id":self.model_id,"display_name":self.display_name,"enabled":not missing,
          "compatibility":"compatible" if not missing else "incompatible","compatibility_errors":[f"Missing required {x}" for x in missing],
          "lookback":self.lookback,"lookback_steps":self.lookback,"horizon":self.horizon,"horizon_steps":self.horizon,
          "input_shape":[self.lookback,len(self.features)],"output_shape":[1],
          "feature_count":len(self.features),"target_name":self.target_name,"target_unit":self.target_unit,
          "parameter_count":PARAMETER_COUNTS.get(self.model_id),
          "probabilistic":self.mc_dropout,"uncertainty_supported":self.mc_dropout,
          "mc_samples":self.mc_samples if self.mc_dropout else None,"q_hat_kw":self.q_hat_kw,
          "predictions_available":bool(self.predictions and self.predictions.is_file()),"artifact_status":"available" if self.artifact.is_file() else "missing"}

def _load(model_id):
    cfg=MODELS_DIR/model_id/"runtime"/"production_config.json"; data=json.loads(cfg.read_text(encoding="utf-8")); package=cfg.parent.parent
    resolve=lambda value: package/value if value else None
    return ModelSpec(model_id,data["display_name"],resolve(data["artifact_path"]),resolve(data["feature_scaler_path"]),
      resolve(data["target_scaler_path"]),cfg,resolve(data.get("predictions_path")),tuple(data["features"]),
      int(data["lookback"]),int(data["horizon"]),data["target_name"],data["target_unit"],bool(data["mc_dropout"]),
      int(data.get("mc_samples",1)),data.get("q_hat_kw"),tuple(data.get("custom_objects",[])))

REGISTRY={model_id:_load(model_id) for model_id in MODEL_IDS}
def get_spec(model_id=None):
    key=model_id or DEFAULT_MODEL_ID
    if key not in REGISTRY: raise KeyError(key)
    return REGISTRY[key]
