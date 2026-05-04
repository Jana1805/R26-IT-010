from fastapi import APIRouter, HTTPException
from app.models.schemas import ScenarioInput, ScenarioOutput
from app.services.prediction_service import process_scenario, save_scenario_result
from datetime import datetime

router = APIRouter()

@router.post("/scenario", response_model=ScenarioOutput)
async def run_scenario(input_data: ScenarioInput):
    """Run scenario analysis with user-defined changes"""
    try:
        # Extract baseline features
        baseline_features = {
            'temperature': input_data.baseline_temperature,
            'rainfall': input_data.baseline_rainfall,
            'humidity': input_data.baseline_humidity,
            'wind_speed': input_data.baseline_wind_speed,
            'public_event': False  # Baseline assumes no public event
        }
        
        # Extract changes
        changes = {
            'temperature_change': input_data.temperature_change,
            'rainfall_change': input_data.rainfall_change,
            'public_event': input_data.public_event
        }
        
        # Process scenario
        result = process_scenario(baseline_features, changes)
        
        # Save to database
        scenario_record = {
            "timestamp": datetime.utcnow(),
            "baseline_features": baseline_features,
            "changes": changes,
            "result": result.dict()
        }
        await save_scenario_result(scenario_record)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario analysis failed: {str(e)}")