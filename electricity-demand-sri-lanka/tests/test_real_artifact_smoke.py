import numpy as np
import pytest
from api.core.model_registry import MODEL_IDS,REGISTRY
from api.services.model_service import ModelService

@pytest.mark.parametrize("model_id",MODEL_IDS)
def test_real_artifact_load_shape_and_one_finite_prediction(model_id):
    service=ModelService(); spec,package=service.load(model_id)
    assert tuple(package.model.input_shape[1:])==(96,20); assert tuple(package.model.output_shape[1:])==(1,)
    raw=np.asarray(package.feature_scaler.mean_,dtype=np.float32)
    scaled=package.feature_scaler.transform(np.tile(raw,(96,1))).astype(np.float32)[None,:,:]
    output=np.asarray(package.model(scaled,training=False)).reshape(-1)
    prediction=package.target_scaler.inverse_transform(output.reshape(-1,1))[0,0]
    assert output.shape==(1,) and np.isfinite(prediction)
