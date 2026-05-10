import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest

PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]


def _load_scaler_if_available(models_dir: Path):
    """Load profile_scaler.pkl with pickle.load if the file exists, else return None."""
    scaler_path = models_dir / "profile_scaler.pkl"
    if scaler_path.exists():
        with open(scaler_path, "rb") as f:
            return pickle.load(f)
    return None


def run_isolation_forest(
    X_scaled: np.ndarray,
    n_estimators: int = 300,
    contamination: float = 0.03,
    random_state: int = 42,
):
    """Fit IsolationForest and return (is_anomaly, anomaly_scores, fitted_model).

    anomaly_score is the negated decision function so higher = more anomalous.
    """
    clf = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    clf.fit(X_scaled)
    anomaly_scores = -clf.decision_function(X_scaled)
    is_anomaly = clf.predict(X_scaled) == -1
    return is_anomaly, anomaly_scores, clf


def run_zscore_anomaly_detection(df: pd.DataFrame, threshold: float = 3.0):
    """Flag rows where |z-score| >= threshold for peak_demand or mean_demand.

    Returns (is_anomaly, peak_z_scores, mean_z_scores).
    """
    peak_z = np.abs(stats.zscore(df["peak_demand"].values, nan_policy="omit"))
    mean_z = np.abs(stats.zscore(df["mean_demand"].values, nan_policy="omit"))
    is_anomaly = (peak_z >= threshold) | (mean_z >= threshold)
    return is_anomaly, peak_z, mean_z


def run_anomaly_detection_pipeline(
    daily_profiles_path: Path,
    cluster_results_path: Path,
    models_dir: Path,
    output_path: Path,
    contamination: float = 0.03,
    zscore_threshold: float = 3.0,
) -> dict:
    """Run IsolationForest and Z-score anomaly detection, combine flags with OR logic.

    Uses the already-fitted profile_scaler (transform only, not fit_transform).

    Saves:
        models_dir/isolation_forest_model.pkl
        output_path (anomaly_results.csv) with columns:
            date, peak_demand, mean_demand, std_demand,
            isolation_anomaly_score, isolation_is_anomaly,
            peak_zscore, mean_zscore, zscore_is_anomaly,
            final_is_anomaly, kmeans_cluster, dbscan_cluster

    Returns summary dict with counts.
    """
    df = pd.read_csv(daily_profiles_path)
    cluster_df = pd.read_csv(cluster_results_path)

    scaler = _load_scaler_if_available(models_dir)
    available = [c for c in PROFILE_COLS if c in df.columns]
    X = df[available].values
    X_scaled = scaler.transform(X)

    iso_is_anomaly, iso_scores, iso_model = run_isolation_forest(
        X_scaled, contamination=contamination
    )
    zscore_is_anomaly, peak_z, mean_z = run_zscore_anomaly_detection(
        df, threshold=zscore_threshold
    )
    final_is_anomaly = iso_is_anomaly | zscore_is_anomaly

    models_dir.mkdir(parents=True, exist_ok=True)
    with open(models_dir / "isolation_forest_model.pkl", "wb") as f:
        pickle.dump(iso_model, f)

    result_df = df[["date", "peak_demand", "mean_demand", "std_demand"]].copy()
    result_df["isolation_anomaly_score"] = iso_scores
    result_df["isolation_is_anomaly"] = iso_is_anomaly
    result_df["peak_zscore"] = peak_z
    result_df["mean_zscore"] = mean_z
    result_df["zscore_is_anomaly"] = zscore_is_anomaly
    result_df["final_is_anomaly"] = final_is_anomaly

    result_df = result_df.merge(
        cluster_df[["date", "kmeans_cluster", "dbscan_cluster"]], on="date", how="left"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)

    return {
        "total_days": len(df),
        "isolation_forest_anomalies": int(iso_is_anomaly.sum()),
        "zscore_anomalies": int(zscore_is_anomaly.sum()),
        "final_anomalies": int(final_is_anomaly.sum()),
        "anomaly_rate_percent": round(float(final_is_anomaly.mean()) * 100, 2),
    }
