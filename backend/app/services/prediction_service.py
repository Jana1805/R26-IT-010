from app.utils.model_loader import predict_demand
from app.database.connection import get_database
from app.models.schemas import ScenarioOutput
import math

def calculate_risk(change_percent: float) -> str:
    """Calculate risk level based on percentage change"""
    if change_percent > 10:
        return "High"
    elif change_percent > 5:
        return "Medium"
    else:
        return "Low"

async def save_scenario_result(scenario_data: dict):
    """Save scenario result to MongoDB"""
    db = get_database()
    if db:
        collection = db.scenarios
        await collection.insert_one(scenario_data)
        print("Scenario result saved to database")

def process_scenario(baseline_features: dict, changes: dict) -> ScenarioOutput:
    """Process scenario prediction with changes"""
    # Calculate scenario features
    scenario_features = baseline_features.copy()
    scenario_features['temperature'] += changes.get('temperature_change', 0)
    scenario_features['rainfall'] += changes.get('rainfall_change', 0)
    scenario_features['public_event'] = changes.get('public_event', False)
    
    # Get predictions
    baseline = predict_demand(baseline_features)
    scenario = predict_demand(scenario_features)
    
    # Calculate change
    change_percent = ((scenario - baseline) / baseline) * 100 if baseline != 0 else 0
    change_percent = round(change_percent, 2)
    
    # Calculate risk
    risk = calculate_risk(abs(change_percent))
    
    return ScenarioOutput(
        baseline=round(baseline, 2),
        scenario=round(scenario, 2),
        change_percent=change_percent,
        risk=risk
    )