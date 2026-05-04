from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import get_settings
from app.database.connection import close_mongo_connection, connect_to_mongo
from app.models.scenario import (
    ScenarioInput, DemandPrediction, RiskAssessment, 
    AIAdvisorResponse, ScenarioResponse, ScenarioComparison
)
from app.services.simulation_engine import DemandSimulationEngine, RiskIntelligenceEngine
from app.services.ai_advisor import AIAdvisorService
from uuid import uuid4
from typing import List

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered decision support system for electricity demand forecasting and scenario analysis",
    version=settings.app_version,
    debug=settings.debug,
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
simulation_engine = DemandSimulationEngine()
risk_engine = RiskIntelligenceEngine()
ai_advisor = AIAdvisorService()

# In-memory storage for scenarios (replace with MongoDB in production)
scenarios_db = {}


@app.on_event("startup")
async def startup_event():
    if settings.db_connect_on_startup:
        await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "AI Electricity Scenario Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "analyze_scenario": "POST /api/scenarios/analyze",
            "compare_scenarios": "POST /api/scenarios/compare",
            "list_scenarios": "GET /api/scenarios",
            "get_scenario": "GET /api/scenarios/{scenario_id}"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AI Electricity Scenario Analysis"}


@app.post("/api/scenarios/analyze", response_model=ScenarioResponse, tags=["Scenario Analysis"])
async def analyze_scenario(scenario_input: ScenarioInput):
    """
    Analyze a given electricity demand scenario
    
    Inputs:
    - temperature_change: Temperature change in °C (-10 to +10)
    - industrial_load_change: Industrial load change in % (-50 to +100)
    - holiday_type: 'holiday', 'weekend', or 'normal'
    - weather_condition: 'rainy', 'sunny', or 'extreme'
    - renewable_energy_contribution: Renewable energy % (0-100)
    
    Returns complete scenario analysis with:
    - Demand predictions
    - Risk assessment
    - AI-generated recommendations and analysis
    """
    # Generate unique scenario ID
    scenario_id = str(uuid4())
    
    # Convert input to dict
    scenario_dict = scenario_input.dict()
    
    # Step 1: Run demand simulation
    prediction_result = simulation_engine.simulate_scenario(scenario_dict)
    prediction = DemandPrediction(**prediction_result)
    
    # Step 2: Assess risk
    risk_result = risk_engine.assess_risk(scenario_dict, prediction_result)
    risk_assessment = RiskAssessment(**risk_result)
    
    # Step 3: Generate AI analysis
    ai_result = ai_advisor.generate_analysis(scenario_dict, prediction_result, risk_result)
    ai_advisor_response = AIAdvisorResponse(**ai_result)
    
    # Construct response
    response = ScenarioResponse(
        scenario_id=scenario_id,
        scenario_input=scenario_input,
        prediction=prediction,
        risk_assessment=risk_assessment,
        ai_advisor=ai_advisor_response
    )
    
    # Store in memory database
    scenarios_db[scenario_id] = response.dict()
    
    return response


@app.post("/api/scenarios/compare", response_model=dict, tags=["Scenario Analysis"])
async def compare_scenarios(
    baseline_input: ScenarioInput,
    modified_input: ScenarioInput
):
    """
    Compare two electricity demand scenarios
    
    Returns comparative analysis including:
    - Demand differences
    - Risk level changes
    - Recommendation on which scenario is better
    """
    # Analyze both scenarios
    baseline = await analyze_scenario(baseline_input)
    modified = await analyze_scenario(modified_input)
    
    # Get comparative analysis from AI advisor
    comparison_result = ai_advisor.compare_scenarios(
        baseline.dict(),
        modified.dict()
    )
    
    return {
        "baseline_scenario": baseline,
        "modified_scenario": modified,
        "comparison": comparison_result,
        "recommendation": f"Choose {('baseline' if comparison_result.get('differences', {}).get('demand_change_mw', 0) > 0 else 'modified')} scenario"
    }


@app.get("/api/scenarios", tags=["Scenario Management"])
async def list_scenarios(limit: int = 10, offset: int = 0):
    """List all stored scenarios with pagination"""
    scenario_list = list(scenarios_db.values())[offset:offset+limit]
    return {
        "total": len(scenarios_db),
        "limit": limit,
        "offset": offset,
        "scenarios": scenario_list
    }


@app.get("/api/scenarios/{scenario_id}", tags=["Scenario Management"])
async def get_scenario(scenario_id: str):
    """Get a specific scenario by ID"""
    if scenario_id not in scenarios_db:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenarios_db[scenario_id]


# Test endpoints
@app.get("/api/test/scenario", tags=["Testing"])
async def test_scenario():
    """Get a test scenario for development"""
    test_input = ScenarioInput(
        temperature_change=3.5,
        industrial_load_change=25,
        holiday_type="normal",
        weather_condition="sunny",
        renewable_energy_contribution=35,
        scenario_name="Test Scenario"
    )
    return await analyze_scenario(test_input)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
