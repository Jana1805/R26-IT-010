"""
Plain-language interpretation of the K-Means clusters, plus the evidence that
explains the clustering comparison.

Clustering is used to DISCOVER and VALIDATE the demand regimes in the data;
the behaviour labels themselves are rule-based for interpretability (see
behavior_labeling.py). Nothing here changes a cluster, a model or a label: it
only reads clustering_results.csv, daily_profiles.csv and anomaly_results.csv
(and, for the comparison insights, refits Ward and GMM exactly as
model_comparison.py does, without touching its cache).
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]

# A cluster is named after the day type that makes up most of it.
WEEKEND_MAJORITY = 0.5

ROLE_NOTE = (
    "Clustering is used to discover and validate the demand regimes in the data "
    "(K-Means finds a weekday pattern and a weekend / low pattern). The behaviour "
    "labels are rule-based for interpretability, so each label can be explained "
    "by a threshold the user can see."
)


def _slot_to_time(slot: int) -> str:
    return f"{slot // 4:02d}:{(slot % 4) * 15:02d}"


def interpret_clusters(daily_profiles_path: Path, clustering_results_path: Path,
                       anomaly_results_path: Path) -> dict:
    """Describe each K-Means cluster: size, weekday / weekend share, demand level,
    peak time of its mean profile, and how many Isolation Forest anomaly days it holds."""
    profiles = pd.read_csv(daily_profiles_path)
    clusters = pd.read_csv(clustering_results_path)[["date", "kmeans_cluster"]]
    anomalies = pd.read_csv(anomaly_results_path)[["date", "final_is_anomaly"]]
    df = profiles.merge(clusters, on="date").merge(anomalies, on="date", how="left")
    df["is_weekend"] = pd.to_datetime(df["date"]).dt.dayofweek >= 5

    result = []
    for cid in sorted(df["kmeans_cluster"].unique()):
        sub = df[df["kmeans_cluster"] == cid]
        weekend_share = float(sub["is_weekend"].mean())
        mean_profile = sub[PROFILE_COLS].mean().values
        is_weekend_pattern = weekend_share >= WEEKEND_MAJORITY
        name = "Weekend / low pattern" if is_weekend_pattern else "Weekday pattern"
        anomaly_days = int(sub["final_is_anomaly"].fillna(False).astype(bool).sum())
        # Days of the minority day type inside the cluster, and how many of those are anomalies
        minority = sub[~sub["is_weekend"]] if is_weekend_pattern else sub[sub["is_weekend"]]
        result.append({
            "cluster": int(cid),
            "name": name,
            "days": int(len(sub)),
            "weekday_share_pct": round((1 - weekend_share) * 100, 1),
            "weekend_share_pct": round(weekend_share * 100, 1),
            "mean_demand_kw": round(float(sub["mean_demand"].mean()), 1),
            "mean_peak_kw": round(float(sub["peak_demand"].mean()), 1),
            "peak_time": _slot_to_time(int(mean_profile.argmax())),
            "trough_time": _slot_to_time(int(mean_profile.argmin())),
            "anomaly_days": anomaly_days,
            "minority_day_type_days": int(len(minority)),
            "minority_day_type_anomalies": int(minority["final_is_anomaly"].fillna(False).astype(bool).sum()),
        })
    return {"clusters": result, "role_note": ROLE_NOTE}


@lru_cache(maxsize=4)
def _clustering_insights_cached(daily_profiles_path: str, clustering_results_path: str,
                                anomaly_results_path: str, _mtimes: tuple) -> dict:
    profiles = pd.read_csv(daily_profiles_path)
    kmeans = pd.read_csv(clustering_results_path)["kmeans_cluster"].values
    anomaly = pd.read_csv(anomaly_results_path)["final_is_anomaly"].astype(bool).values
    X_scaled = StandardScaler().fit_transform(profiles[PROFILE_COLS].values)

    # Same settings as model_comparison.py (_run_agglomerative, _run_gaussian_mixture)
    ward = AgglomerativeClustering(n_clusters=2, linkage="ward").fit_predict(X_scaled)
    gmm = GaussianMixture(n_components=2, random_state=42).fit_predict(X_scaled)

    gmm_sizes = np.bincount(gmm)
    small = int(np.argmin(gmm_sizes))
    small_size = int(gmm_sizes[small])
    small_anomalies = int(anomaly[gmm == small].sum())
    ward_ari = round(float(adjusted_rand_score(kmeans, ward)), 3)
    gmm_ari = round(float(adjusted_rand_score(kmeans, gmm)), 3)

    return {
        "ward_ari_vs_kmeans": ward_ari,
        "ward_cluster_sizes": sorted(np.bincount(ward).tolist(), reverse=True),
        "gmm_ari_vs_kmeans": gmm_ari,
        "gmm_cluster_sizes": sorted(gmm_sizes.tolist(), reverse=True),
        "gmm_small_cluster_size": small_size,
        "gmm_small_cluster_anomaly_days": small_anomalies,
        "gmm_explanation": (
            f"GMM has the highest silhouette because it separates a small group of "
            f"{small_size} days, {small_anomalies} of which are Isolation Forest anomaly days, "
            f"from all other days ({int(gmm_sizes.max())}). That is an anomaly split, not a "
            f"behaviour split (agreement with K-Means: ARI {gmm_ari}), so GMM ranks last on "
            f"Davies-Bouldin and Calinski-Harabasz and is not selected."
        ),
        "ward_explanation": (
            f"Ward agglomerative clustering finds almost the same two groups as K-Means "
            f"(ARI {ward_ari}), which independently confirms the weekday / weekend split."
        ),
    }


def clustering_insights(daily_profiles_path: Path, clustering_results_path: Path,
                        anomaly_results_path: Path) -> dict:
    """Ward and GMM agreement with K-Means, computed once per backend run (and
    again only if one of the input CSVs changes)."""
    paths = [Path(daily_profiles_path), Path(clustering_results_path), Path(anomaly_results_path)]
    mtimes = tuple(p.stat().st_mtime for p in paths)
    return _clustering_insights_cached(*(str(p) for p in paths), mtimes)
