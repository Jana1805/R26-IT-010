from app.core.config import (
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    MODELS_DIR,
    RAW_DATASET_FILENAME,
)
from app.ml.anomaly_detection import run_anomaly_detection_pipeline
from app.ml.behavior_labeling import generate_behavior_labels_from_csv
from app.ml.behavior_prediction import predict_future_behavior
from app.ml.clustering import run_clustering_pipeline
from app.ml.daily_profile import to_daily_profiles
from app.ml.data_loader import load_raw_dataset
from app.ml.peak_detection import detect_peak_days
from app.ml.preprocessing import preprocess_timeseries
from app.services import analysis_service


def run_generate_daily_profiles() -> dict:
    """Load raw CSV, preprocess, extract daily profiles, save cleaned.csv and daily_profiles.csv."""
    try:
        DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        df_raw, ts_col, demand_col = load_raw_dataset(DATA_RAW_DIR / RAW_DATASET_FILENAME)
        df_clean = preprocess_timeseries(df_raw, ts_col, demand_col)
        df_clean.to_csv(DATA_PROCESSED_DIR / "cleaned.csv", index=False)

        daily_profiles = to_daily_profiles(df_clean)
        daily_profiles.to_csv(DATA_PROCESSED_DIR / "daily_profiles.csv", index=False)

        return {
            "success": True,
            "message": "Daily profiles generated successfully.",
            "data": {
                "raw_rows": len(df_raw),
                "cleaned_rows": len(df_clean),
                "profile_days": len(daily_profiles),
            },
        }
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}


def run_clustering() -> dict:
    """Run KMeans + DBSCAN clustering on daily profiles."""
    try:
        result = run_clustering_pipeline(
            daily_profiles_path=DATA_PROCESSED_DIR / "daily_profiles.csv",
            models_dir=MODELS_DIR,
            output_path=DATA_PROCESSED_DIR / "cluster_results.csv",
        )
        return {"success": True, "message": "Clustering completed successfully.", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}


def run_anomaly_detection() -> dict:
    """Run IsolationForest + Z-score anomaly detection."""
    try:
        result = run_anomaly_detection_pipeline(
            daily_profiles_path=DATA_PROCESSED_DIR / "daily_profiles.csv",
            cluster_results_path=DATA_PROCESSED_DIR / "cluster_results.csv",
            models_dir=MODELS_DIR,
            output_path=DATA_PROCESSED_DIR / "anomaly_results.csv",
        )
        return {
            "success": True,
            "message": "Anomaly detection completed successfully.",
            "data": result,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}


def run_peak_detection() -> dict:
    """Detect peak demand days using percentile + anomaly thresholds."""
    try:
        result = detect_peak_days(
            daily_profiles_path=DATA_PROCESSED_DIR / "daily_profiles.csv",
            anomaly_results_path=DATA_PROCESSED_DIR / "anomaly_results.csv",
            output_path=DATA_PROCESSED_DIR / "peak_demand_results.csv",
        )
        return {
            "success": True,
            "message": "Peak detection completed successfully.",
            "data": result,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}


def run_behavior_labeling() -> dict:
    """Assign behaviour labels to all days."""
    try:
        result = generate_behavior_labels_from_csv(
            peak_demand_results_path=DATA_PROCESSED_DIR / "peak_demand_results.csv",
            output_path=DATA_PROCESSED_DIR / "behavior_labels.csv",
        )
        return {
            "success": True,
            "message": "Behaviour labeling completed successfully.",
            "data": result,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}


def get_dashboard_summary() -> dict:
    """Return the full dashboard KPI summary."""
    try:
        result = analysis_service.get_dashboard_summary()
        return {"success": True, "message": "Dashboard summary loaded.", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}


def get_prediction(date_str: str) -> dict:
    """Predict the behaviour label for a future date."""
    try:
        result = predict_future_behavior(
            behavior_labels_path=DATA_PROCESSED_DIR / "behavior_labels.csv",
            target_date_str=date_str,
        )
        return {
            "success": True,
            "message": f"Prediction for {date_str} generated.",
            "data": result,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}


def get_day_profile(date_str: str) -> dict:
    """Return the 96-slot load profile and behaviour metadata for a single date."""
    try:
        result = analysis_service.get_day_profile(date_str)
        return {"success": True, "message": f"Profile for {date_str} loaded.", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}
