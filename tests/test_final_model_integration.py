from types import SimpleNamespace
from dataclasses import replace
from unittest.mock import Mock
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from api.core.model_registry import DEFAULT_MODEL_ID, MODEL_IDS, REGISTRY
from api.main import app
from api.services.model_service import LoadedPackage, ModelService, ModelServiceError
from api.services.prediction_comparison import align_prediction_files, calculate_metrics

def test_registry_contains_all_seven_stable_ids():
    assert tuple(REGISTRY)==MODEL_IDS; assert DEFAULT_MODEL_ID in REGISTRY
    assert all(spec.lookback==96 and spec.horizon==1 and len(spec.features)==20 for spec in REGISTRY.values())
def test_every_model_uses_its_own_declared_scaler_paths():
    assert all(spec.feature_scaler.parent.parent.name==model_id for model_id,spec in REGISTRY.items())
    assert len({str(spec.feature_scaler) for spec in REGISTRY.values()})==7
def test_registry_reports_artifact_and_uncertainty_status():
    statuses=[spec.public_status() for spec in REGISTRY.values()]
    assert all(x["artifact_status"]=="available" for x in statuses)
    assert {x["model_id"] for x in statuses if x["uncertainty_supported"]}=={"cnn_lstm_mc","cnn_transformer_mc"}
def test_missing_artifact_is_disabled(monkeypatch,tmp_path):
    spec=replace(REGISTRY["cnn"],artifact=tmp_path/"missing.keras")
    assert not spec.enabled and spec.public_status()["compatibility"]=="incompatible"
def _mock_service(monkeypatch,mc=False):
    service=ModelService(); spec=REGISTRY["cnn_lstm_mc" if mc else "cnn"]
    model=Mock(); model.layers=[]; model.return_value=np.array([[0.5]],dtype=np.float32)
    fs=Mock(n_features_in_=20); fs.transform.side_effect=lambda x:x
    ts=Mock(n_features_in_=1,scale_=np.array([10.])); ts.inverse_transform.side_effect=lambda x:np.asarray(x)*10+100
    monkeypatch.setattr(service,"load",lambda _: (spec,LoadedPackage(model,fs,ts)))
    return service,spec,model
def test_deterministic_inference_contract_and_feature_order(monkeypatch):
    service,spec,model=_mock_service(monkeypatch); values=np.zeros((96,20))
    result=service.predict("cnn",values,"2026-01-01",list(spec.features))
    assert result["predicted_load_kw"]==105 and result["uncertainty"] is None
    model.assert_called_once(); assert model.call_args.kwargs["training"] is False
    with pytest.raises(ModelServiceError,match="required order"): service.predict("cnn",values,"x",list(reversed(spec.features)))
def test_input_shape_and_finite_validation(monkeypatch):
    service,spec,_=_mock_service(monkeypatch)
    with pytest.raises(ModelServiceError) as exc: service.predict("cnn",np.zeros((95,20)),"x"); assert exc.value.code=="invalid_input_shape"
    values=np.zeros((96,20)); values[0,0]=np.nan
    with pytest.raises(ModelServiceError) as exc: service.predict("cnn",values,"x"); assert exc.value.code=="non_finite_input"
def test_mc_dropout_batches_stochastic_samples(monkeypatch):
    service,spec,model=_mock_service(monkeypatch,mc=True); values=np.zeros((96,20))
    result=service.predict(spec.model_id,values,"x",list(spec.features))
    model.assert_called_once(); assert model.call_args.kwargs["training"] is True
    assert model.call_args.args[0].shape==(spec.mc_samples,96,20)
    assert result["uncertainty"]["samples"]==spec.mc_samples
def test_mc_dropout_honors_sample_override(monkeypatch):
    service,spec,model=_mock_service(monkeypatch,mc=True); values=np.zeros((96,20))
    result=service.predict(spec.model_id,values,"x",list(spec.features),mc_samples=5)
    assert model.call_args.args[0].shape==(5,96,20)
    assert result["uncertainty"]["samples"]==5
def test_cache_returns_same_package(monkeypatch):
    service=ModelService(); spec=REGISTRY["cnn"]
    fake=LoadedPackage(SimpleNamespace(input_shape=(None,96,20),output_shape=(None,1)),SimpleNamespace(n_features_in_=20),SimpleNamespace(n_features_in_=1))
    calls=Mock(side_effect=[fake.feature_scaler,fake.target_scaler]); monkeypatch.setattr("api.services.model_service.joblib.load",calls)
    monkeypatch.setattr("api.services.model_service.tf.keras.models.load_model",lambda *a,**k:fake.model)
    first=service.load("cnn")[1]; second=service.load("cnn")[1]
    assert first is second and calls.call_count==2
def test_api_models_and_invalid_id():
    client=TestClient(app); body=client.get("/api/models").json()
    assert body["default_model_id"]==DEFAULT_MODEL_ID and len(body["models"])==7
    response=client.post("/api/predict",json={"model_id":"nope","values":[[0]*20]*96,"forecast_timestamp":"x"})
    assert response.status_code==404 and response.json()["detail"]["code"]=="invalid_model_id"
def test_prediction_csv_alignment_and_recalculated_metrics():
    aligned,unavailable=align_prediction_files(); metrics=calculate_metrics(aligned)
    assert len(aligned)==18817 and len(metrics)==6
    assert unavailable=={"cnn_lstm_mc":"Predictions CSV unavailable"}
    assert list(metrics["rank"])==list(range(1,7)) and np.isfinite(metrics[["MAE","RMSE","MAPE","R2"]]).all().all()
