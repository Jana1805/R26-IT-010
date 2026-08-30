"""Lazy, cached, model-specific loading and inference."""
import logging, threading, time
from dataclasses import dataclass
import joblib, numpy as np, tensorflow as tf
from api.core.model_registry import get_spec
from api.services.custom_layers import PositionalEncoding, TransformerBlock

logger=logging.getLogger(__name__)
CUSTOM_OBJECTS={"PositionalEncoding":PositionalEncoding,"TransformerBlock":TransformerBlock,
 "LoadForecasting>PositionalEncoding":PositionalEncoding,"LoadForecasting>TransformerBlock":TransformerBlock}
class ModelServiceError(RuntimeError):
    def __init__(self,code,message): super().__init__(message); self.code=code
@dataclass
class LoadedPackage: model:object; feature_scaler:object; target_scaler:object

class ModelService:
    def __init__(self): self._cache={}; self._lock=threading.RLock()
    @property
    def loaded_model_ids(self): return sorted(self._cache)
    def clear(self):
        with self._lock: self._cache.clear()
    def load(self,model_id=None):
        try: spec=get_spec(model_id)
        except KeyError: raise ModelServiceError("invalid_model_id","The requested model is not registered")
        if not spec.enabled: raise ModelServiceError("model_unavailable","The requested model package is incomplete")
        with self._lock:
            if spec.model_id in self._cache: return spec,self._cache[spec.model_id]
            try:
                fs=joblib.load(spec.feature_scaler); ts=joblib.load(spec.target_scaler)
                model=tf.keras.models.load_model(spec.artifact,custom_objects=CUSTOM_OBJECTS,compile=False,safe_mode=False)
                self._validate(spec,model,fs,ts)
            except ModelServiceError: raise
            except Exception as exc:
                logger.exception("Package load failed for %s",spec.model_id)
                raise ModelServiceError("model_load_failed",f"Model '{spec.model_id}' could not be loaded") from exc
            package=LoadedPackage(model,fs,ts); self._cache[spec.model_id]=package
            logger.info("Loaded model package %s",spec.model_id); return spec,package
    @staticmethod
    def _validate(spec,model,fs,ts):
        if tuple(model.input_shape[1:])!=(spec.lookback,len(spec.features)): raise ModelServiceError("shape_mismatch","Model input shape does not match configuration")
        if tuple(model.output_shape[1:])!=(1,): raise ModelServiceError("shape_mismatch","Model output shape does not match horizon 1")
        if int(getattr(fs,"n_features_in_",-1))!=len(spec.features): raise ModelServiceError("scaler_mismatch","Feature scaler dimension does not match configuration")
        if int(getattr(ts,"n_features_in_",-1))!=1: raise ModelServiceError("scaler_mismatch","Target scaler must contain one feature")
    def predict(self,model_id,values,forecast_timestamp,feature_names=None,mc_samples=None):
        spec,pkg=self.load(model_id); x=np.asarray(values,dtype=np.float32)
        if x.shape!=(spec.lookback,len(spec.features)): raise ModelServiceError("invalid_input_shape",f"Expected input shape {(spec.lookback,len(spec.features))}")
        if feature_names is not None and tuple(feature_names)!=spec.features: raise ModelServiceError("invalid_feature_order","Features are not in the required order")
        if not np.isfinite(x).all(): raise ModelServiceError("non_finite_input","Input contains NaN or infinite values")
        started=time.perf_counter(); scaled=pkg.feature_scaler.transform(x).astype(np.float32)[None,:,:]
        if spec.mc_dropout:
            if any(isinstance(layer,tf.keras.layers.BatchNormalization) for layer in pkg.model.layers): raise ModelServiceError("unsafe_mc_dropout","MC inference is disabled for models containing BatchNormalization")
            sample_count=spec.mc_samples if mc_samples is None else int(mc_samples)
            if not 1 <= sample_count <= 100: raise ModelServiceError("invalid_mc_samples","MC samples must be between 1 and 100")
            # A single batched forward pass gives every batch item an independent
            # dropout mask while avoiding one TensorFlow/Python call per sample.
            mc_input=np.repeat(scaled,sample_count,axis=0)
            samples=np.asarray(pkg.model(mc_input,training=True),dtype=np.float32).reshape(-1)
            mean_scaled=float(samples.mean()); std_scaled=float(samples.std())
        else: mean_scaled=float(np.asarray(pkg.model(scaled,training=False)).reshape(-1)[0]); std_scaled=None
        prediction=float(pkg.target_scaler.inverse_transform([[mean_scaled]])[0,0])
        result={"model_id":spec.model_id,"display_name":spec.display_name,"forecast_timestamp":str(forecast_timestamp),
          "predicted_load_kw":prediction,"horizon":spec.horizon,"inference_time_ms":round((time.perf_counter()-started)*1000,3),"uncertainty":None}
        if std_scaled is not None:
            std_kw=float(std_scaled*pkg.target_scaler.scale_[0]); result["uncertainty"]={"method":"mc_dropout","samples":sample_count,"predictive_std_kw":std_kw,"lower_kw":None,"upper_kw":None}
            if spec.q_hat_kw is not None: result["uncertainty"].update(method="mc_dropout_with_validation_residual_calibration",lower_kw=prediction-spec.q_hat_kw,upper_kw=prediction+spec.q_hat_kw)
        return result
model_service=ModelService()
