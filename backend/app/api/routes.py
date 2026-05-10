from fastapi import APIRouter, Query
from backend.app.controllers import pipeline_controller

router = APIRouter()

@router.post("/generate-daily-profiles")
def generate_daily_profiles():
    return pipeline_controller.run_generate_daily_profiles()

@router.post("/run-clustering")
def run_clustering():
    return pipeline_controller.run_clustering()

@router.post("/run-anomaly-detection")
def run_anomaly_detection():
    return pipeline_controller.run_anomaly_detection()

@router.post("/detect-peak-days")
def detect_peak_days():
    return pipeline_controller.run_peak_detection()

@router.post("/generate-behavior-labels")
def generate_behavior_labels():
    return pipeline_controller.run_behavior_labeling()

@router.get("/dashboard-summary")
def dashboard_summary():
    return pipeline_controller.get_dashboard_summary()

@router.get("/predict-future-behavior")
def predict_future_behavior(date: str = Query(..., description="Target date e.g. 2025-08-14")):
    return pipeline_controller.get_prediction(date)

@router.get("/get-day-profile")
def get_day_profile(date: str = Query(..., description="Date string e.g. 2020-03-15")):
    return pipeline_controller.get_day_profile(date)
