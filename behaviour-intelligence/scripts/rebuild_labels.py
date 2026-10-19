"""
Rebuild peak days and behaviour labels with the API's own modules (stages 4-5
of pipeline_runner), WITHOUT touching data loading, clustering or anomaly
detection: daily_profiles.csv, clustering_results.csv, anomaly_results.csv and
every .pkl / comparison cache are read, never written.

Also writes the two summary JSONs from the current outputs:
    models/behavior_label_summary.json
    models/anomaly_metrics.json

Use this instead of backend/app/ml/train_models.py (deprecated).

    cd behaviour-intelligence/backend
    ..\\.venv\\Scripts\\python.exe ..\\scripts\\rebuild_labels.py
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

import pandas as pd  # noqa: E402

from app.core.config import DATA_PROCESSED_DIR, MODELS_DIR  # noqa: E402
from app.ml.behavior_labeling import generate_behavior_labels_from_csv  # noqa: E402
from app.ml.peak_detection import detect_peak_days  # noqa: E402


def main():
    peak = detect_peak_days(
        daily_profiles_path=DATA_PROCESSED_DIR / "daily_profiles.csv",
        anomaly_results_path=DATA_PROCESSED_DIR / "anomaly_results.csv",
        output_path=DATA_PROCESSED_DIR / "peak_demand_results.csv",
    )
    labels = generate_behavior_labels_from_csv(
        peak_demand_results_path=DATA_PROCESSED_DIR / "peak_demand_results.csv",
        output_path=DATA_PROCESSED_DIR / "behavior_labels.csv",
    )
    with open(MODELS_DIR / "behavior_label_summary.json", "w") as f:
        json.dump({**labels, "peak_detection": peak}, f, indent=2)

    anomalies = pd.read_csv(DATA_PROCESSED_DIR / "anomaly_results.csv")
    total = len(anomalies)
    iso = int(anomalies["isolation_is_anomaly"].astype(bool).sum())
    final = int(anomalies["final_is_anomaly"].astype(bool).sum())
    with open(MODELS_DIR / "anomaly_metrics.json", "w") as f:
        json.dump({
            "total_days": total,
            "isolation_forest_anomaly_count": iso,
            "z_score_anomaly_count": int(anomalies["zscore_is_anomaly"].astype(bool).sum()),
            "final_anomaly_count": final,
            "anomaly_percentage": round(final / total * 100, 2),
            "final_rule": "final_is_anomaly = Isolation Forest only; z-score columns are diagnostics",
            "source": "data/processed/anomaly_results.csv (written by app.ml.anomaly_detection)",
        }, f, indent=2)

    print(json.dumps({"peak_detection": peak, "labels": labels}, indent=2))


if __name__ == "__main__":
    main()
