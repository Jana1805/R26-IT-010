from pathlib import Path

from app.core.config import RAW_DATASET_FILENAME
from app.ml.anomaly_detection import run_anomaly_detection_pipeline
from app.ml.behavior_labeling import generate_behavior_labels_from_csv
from app.ml.clustering import run_clustering_pipeline
from app.ml.daily_profile import to_daily_profiles
from app.ml.data_loader import load_raw_dataset
from app.ml.peak_detection import detect_peak_days
from app.ml.preprocessing import preprocess_timeseries


def run_full_pipeline(
    data_raw_dir: Path,
    data_processed_dir: Path,
    models_dir: Path,
) -> dict:
    """Execute the complete 5-stage ML pipeline end-to-end.

    Stage 1 — Data preparation:   load raw CSV → clean → extract 96-slot daily profiles
    Stage 2 — Clustering:         KMeans (auto-k) + DBSCAN on scaled profile vectors
    Stage 3 — Anomaly detection:  IsolationForest + Z-score, combined with OR logic
    Stage 4 — Peak detection:     percentile + z-score + anomaly thresholds
    Stage 5 — Behaviour labeling: priority-rule assignment of demand behaviour labels

    All intermediate CSVs are written to data_processed_dir.
    All serialised models (.pkl) are written to models_dir.

    Returns a summary dict with results from each stage.
    """
    data_processed_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    # --- Stage 1 ---
    raw_path = data_raw_dir / RAW_DATASET_FILENAME
    df_raw, ts_col, demand_col = load_raw_dataset(raw_path)
    df_clean = preprocess_timeseries(df_raw, ts_col, demand_col)

    cleaned_path = data_processed_dir / "cleaned.csv"
    df_clean.to_csv(cleaned_path, index=False)

    daily_profiles = to_daily_profiles(df_clean)
    profiles_path = data_processed_dir / "daily_profiles.csv"
    daily_profiles.to_csv(profiles_path, index=False)

    stage1 = {
        "raw_rows": len(df_raw),
        "cleaned_rows": len(df_clean),
        "profile_days": len(daily_profiles),
    }

    # --- Stage 2 ---
    cluster_output = data_processed_dir / "cluster_results.csv"
    stage2 = run_clustering_pipeline(
        daily_profiles_path=profiles_path,
        models_dir=models_dir,
        output_path=cluster_output,
    )

    # --- Stage 3 ---
    anomaly_output = data_processed_dir / "anomaly_results.csv"
    stage3 = run_anomaly_detection_pipeline(
        daily_profiles_path=profiles_path,
        cluster_results_path=cluster_output,
        models_dir=models_dir,
        output_path=anomaly_output,
    )

    # --- Stage 4 ---
    peak_output = data_processed_dir / "peak_demand_results.csv"
    stage4 = detect_peak_days(
        daily_profiles_path=profiles_path,
        anomaly_results_path=anomaly_output,
        output_path=peak_output,
    )

    # --- Stage 5 ---
    labels_output = data_processed_dir / "behavior_labels.csv"
    stage5 = generate_behavior_labels_from_csv(
        peak_demand_results_path=peak_output,
        output_path=labels_output,
    )

    return {
        "stage1_data_preparation": stage1,
        "stage2_clustering": stage2,
        "stage3_anomaly_detection": stage3,
        "stage4_peak_detection": stage4,
        "stage5_behavior_labeling": stage5,
    }
