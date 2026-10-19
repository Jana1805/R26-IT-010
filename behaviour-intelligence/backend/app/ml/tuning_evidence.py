"""Read-only access to the hyperparameter tuning evidence produced by
notebooks/07_hyperparameter_tuning.ipynb.

The notebook writes CSV tables to thesis_evidence/tables_v2/ and PNG figures
to thesis_evidence/figures_v2/ (workspace root, next to behaviour-intelligence/).
This module only reads those files; it never runs the tuning itself."""
from pathlib import Path

import pandas as pd

from app.core.config import TUNING_TABLES_DIR, TUNING_FIGURES_DIR

PRINCIPLE = (
    "Every parameter was first chosen WITHOUT labels (cluster quality indices, BIC, the "
    "k-distance knee, and stability when the model is refitted on random 80% samples of the days). "
    "Only afterwards were the choices checked against the known ground truth of this synthetic "
    "dataset: the 60 anomaly days injected by notebook 06, and the weekday / weekend difference."
)

HONEST_LIMITS = [
    "The dataset is synthetic with clear whole-day anomalies, so the perfect anomaly scores would be lower on real data.",
    "Contamination 0.03 is equal to the injected anomaly rate (60 / 1,977 = 3.03%).",
    "The future prediction is only slightly better than a simple weekend rule.",
]

# One entry per notebook section: tables, figures and plain-English notes.
SECTIONS = [
    {
        "id": "kmeans",
        "title": "1. K-Means: number of clusters k",
        "what": "K-Means needs the number of groups (k) in advance. We tried k = 2 to 12 and scored each with "
                "three quality indices (silhouette, Davies–Bouldin, Calinski–Harabasz), the elbow of the inertia "
                "curve, and stability over 10 random seeds.",
        "result": "All three indices pick k = 2. The two clusters are weekdays and weekends: they match the weekend "
                  "flag with ARI 0.965, and 1.0 when the 60 anomaly days are left out.",
        "chosen": "k = 2",
        "tables": ["T01_kmeans_k_tuning.csv"],
        "figures": ["F01_kmeans_k_tuning.png"],
    },
    {
        "id": "gmm",
        "title": "2. Gaussian Mixture: components and covariance type",
        "what": "A Gaussian Mixture needs the number of components and the covariance type. We tried 1–6 components "
                "with four covariance types and compared them with BIC (lower is better) and AIC.",
        "result": "BIC picks 3 full-covariance components, but these model the anomaly days, not behaviour (ARI vs "
                  "weekend 0.07). The 2-component GMM puts 36 of the 60 anomaly days in a small group of 37.",
        "chosen": "Not used in production (comparison only)",
        "tables": ["T02_gmm_bic_aic.csv"],
        "figures": ["F02_gmm_bic.png"],
    },
    {
        "id": "ward",
        "title": "3. Ward clustering: number of clusters",
        "what": "Ward (hierarchical) clustering also needs k. We tried k = 2 to 8 and measured how much it agrees "
                "with K-Means.",
        "result": "Ward is also best at k = 2 and agrees with K-Means with ARI 0.957. A different algorithm finds the "
                  "same two groups, so the split is real.",
        "chosen": "k = 2 (comparison only)",
        "tables": ["T03_ward_k_tuning.csv"],
        "figures": ["F03_ward_k_tuning.png"],
    },
    {
        "id": "dbscan",
        "title": "4. DBSCAN: eps and min_samples",
        "what": "DBSCAN needs a radius (eps) and a minimum number of neighbours (min_samples). We took eps from the "
                "k-distance curve at several percentiles and at the knee, for min_samples 4, 8 and 16.",
        "result": "Small eps marks most days as noise; large eps merges everything into one cluster. At the knee, "
                  "DBSCAN gives 1 cluster plus 60 noise days, and those are exactly the 60 injected anomaly days.",
        "chosen": "eps = knee (4.4183), min_samples = 8",
        "tables": ["T04_dbscan_eps_minsamples.csv"],
        "figures": ["F04_dbscan_heatmap.png"],
    },
    {
        "id": "iforest",
        "title": "5. Isolation Forest: contamination, trees, max_samples",
        "what": "We tried contamination 0.01–0.05 × 100/200/300/500 trees × max_samples 128/256/auto. Each setting "
                "was refitted on 20 random 80% samples to measure how stable the flagged days are (selection), "
                "then checked against the 60 injected anomaly days (validation).",
        "result": "Contamination 0.03 is the most stable rate, and the number of trees and max_samples make no "
                  "difference. At 0.03 precision = recall = 1.0. Two methods that need no rate at all "
                  "(contamination=\"auto\" and the largest gap in the scores) flag the same 60 days.",
        "chosen": "contamination 0.03, 300 trees, max_samples auto",
        "note": "Honest note: 0.03 equals the injected rate, and the anomalies in this dataset are very clear.",
        "tables": ["T06_isolation_forest_by_contamination.csv", "T07_isolation_forest_score_threshold.csv",
                   "T05_isolation_forest_grid.csv"],
        "figures": ["F05_isolation_forest_tuning.png", "F06_isolation_forest_score_gap.png"],
    },
    {
        "id": "lof-ocsvm",
        "title": "6. LOF and One-Class SVM",
        "what": "The two comparison detectors were tuned in the same way: LOF n_neighbors (5–50), and One-Class SVM "
                "nu × gamma.",
        "result": "LOF flags the same 60 days for every n_neighbors. The One-Class SVM is very sensitive to gamma: "
                  "the app setting (gamma = scale) reaches only precision 0.40 / recall 0.50, while gamma = 0.001 "
                  "reaches F1 0.99. A simple z-score finds none of the anomaly days.",
        "chosen": "Isolation Forest stays the production detector",
        "tables": ["T10_detector_comparison.csv", "T08_lof_n_neighbors.csv", "T09_ocsvm_nu_gamma.csv"],
        "figures": ["F07_detector_comparison.png"],
    },
    {
        "id": "thresholds",
        "title": "7. Threshold sensitivity",
        "what": "The labels use the percentiles p90 (peak), p75 (anomaly with a high peak) and p25 (low demand). "
                "We moved each one by ±5 points to see how much the labels change.",
        "result": "The counts change gradually, with no sudden jumps. p90 is the most sensitive, as expected. At p25 "
                  "every Low Demand Day is a weekend.",
        "chosen": "p90 / p75 / p25",
        "tables": ["T11_threshold_sensitivity.csv"],
        "figures": ["F08_threshold_sensitivity.png"],
    },
    {
        "id": "prediction",
        "title": "8. Future prediction back-test",
        "what": "Trained on days before 2024-06-01 and predicted the next 364 days, comparing the app's method "
                "(month + day-of-week) with simple baselines.",
        "result": "The app's method has the best accuracy (83.5% vs 62.4% for the majority label). But the simple rule "
                  "\"weekend → Low, weekday → Normal\" already reaches 83.0%. Abnormal days cannot be predicted "
                  "from the calendar.",
        "chosen": "month + day-of-week",
        "tables": ["T12_prediction_backtest.csv"],
        "figures": ["F09_prediction_backtest.png"],
    },
    {
        "id": "summary",
        "title": "9. Final parameter summary",
        "what": "Every parameter of the pipeline, how it was chosen, where the evidence is, and why.",
        "result": "",
        "chosen": "",
        "tables": ["T13_final_parameter_summary.csv"],
        "figures": [],
    },
]

TABLE_TITLES = {
    "T01_kmeans_k_tuning.csv": "K-Means: quality indices for k = 2–12",
    "T02_gmm_bic_aic.csv": "GMM: BIC and AIC by components and covariance type",
    "T03_ward_k_tuning.csv": "Ward: quality indices and agreement with K-Means",
    "T04_dbscan_eps_minsamples.csv": "DBSCAN: clusters and noise for each setting",
    "T05_isolation_forest_grid.csv": "Isolation Forest: full grid (60 settings), most stable first",
    "T06_isolation_forest_by_contamination.csv": "Isolation Forest: average per contamination rate",
    "T07_isolation_forest_score_threshold.csv": "Isolation Forest: threshold-free alternatives",
    "T08_lof_n_neighbors.csv": "LOF: n_neighbors",
    "T09_ocsvm_nu_gamma.csv": "One-Class SVM: nu × gamma",
    "T10_detector_comparison.csv": "All detectors against the 60 injected anomaly days",
    "T11_threshold_sensitivity.csv": "Label counts when one threshold moves by 5 points",
    "T12_prediction_backtest.csv": "Back-test: app method vs baselines",
    "T13_final_parameter_summary.csv": "Final parameter summary",
}

FIGURE_NAMES = {f for s in SECTIONS for f in s["figures"]}
TABLE_NAMES = set(TABLE_TITLES)


def read_table(name: str) -> dict:
    """One evidence table as {name, title, columns, rows}; NaN becomes null."""
    path = TUNING_TABLES_DIR / name
    if name not in TABLE_NAMES or not path.exists():
        return {"name": name, "title": TABLE_TITLES.get(name, name), "available": False, "columns": [], "rows": []}
    df = pd.read_csv(path, keep_default_na=True)
    df = df.astype(object).where(pd.notna(df), None)
    if "best" in df.columns:
        df["best"] = df["best"].map(lambda v: v or "")
    return {
        "name": name,
        "title": TABLE_TITLES[name],
        "available": True,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }


def figure_path(name: str) -> Path | None:
    """Path of an evidence figure, only for known names (no arbitrary file access)."""
    if name not in FIGURE_NAMES:
        return None
    path = TUNING_FIGURES_DIR / name
    return path if path.exists() else None


def get_tuning_evidence() -> dict:
    """All sections with their notes, tables and figure availability."""
    sections = []
    for s in SECTIONS:
        sections.append({
            **{k: v for k, v in s.items() if k not in ("tables", "figures")},
            "tables": [read_table(t) for t in s["tables"]],
            "figures": [{"name": f, "available": figure_path(f) is not None} for f in s["figures"]],
        })
    available = TUNING_TABLES_DIR.exists() and any(t["available"] for s in sections for t in s["tables"])
    return {
        "available": available,
        "source_notebook": "notebooks/07_hyperparameter_tuning.ipynb",
        "tables_dir": str(TUNING_TABLES_DIR),
        "figures_dir": str(TUNING_FIGURES_DIR),
        "principle": PRINCIPLE,
        "honest_limits": HONEST_LIMITS,
        "sections": sections,
    }
