from fastapi import APIRouter, HTTPException
from app.models.schemas import PredictionInput, PredictionOutput
from app.utils.model_loader import predict_demand

router = APIRouter()

@router.post("/predict", response_model=PredictionOutput)
async def predict_electricity_demand(input_data: PredictionInput):
    """Predict electricity demand based on input features"""
    try:
        features = input_data.dict()
        prediction = predict_demand(features)
        return PredictionOutput(predicted_demand=round(prediction, 2))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")