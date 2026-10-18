import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]

# DBSCAN diagnosis on daily_profiles.csv (1977 days, 96-dim scaled profiles,
# k=8 matching min_samples=8): the 8th-nearest-neighbour distance curve is
# flat from p50=3.72 to p95=4.30, then jumps to p99=33.44 -- a long thin
# tail, not a second density peak. A full eps x min_samples sweep (eps
# spanning the knee, min_samples in {4, 8, 16}) found no eps giving both
# >=2 clusters and noise below 25%: eps <= ~3.7 yields multiple clusters
# but 29-94% noise with silhouette 0.15-0.23 on what remains; eps >= the
# knee collapses to exactly 1 cluster for every min_samples tested. At
# eps >= knee, the ~60 noise days coincide exactly with the Isolation
# Forest and LOF anomaly sets (see anomaly_comparison.py's bootstrap
# stability ranking) -- that is univariate outlier detection wearing
# DBSCAN's clothes, not density-based segmentation. eps is therefore set
# directly from the k-distance knee (max perpendicular distance from the
# chord connecting the sorted curve's endpoints, computed at runtime)
# instead of the previous fallback loop that retried eps += 0.4 until any
# single point escaped noise status -- which is how it silently settled on
# eps=2.80, below the 50th percentile of k-distance, and reported a
# "cluster" of 21 points as if it were a meaningful result.


def _select_best_k(X_scaled: np.ndarray, k_min: int = 2, k_max: int = 12):
    """Try KMeans for each k in [k_min, k_max] and return (best_k, best_silhouette_score)."""
    best_k = k_min
    best_score = -1.0
    scores = {}
    for k in range(k_min, k_max + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init=20).fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        scores[k] = round(float(score), 4)
        if score > best_score:
            best_score = score
            best_k = k
    return best_k, best_score, scores


def _compute_knee_eps(X_scaled: np.ndarray, k: int) -> tuple:
    """Compute eps from the k-distance knee.

    Distance to each point's k-th nearest OTHER point, sorted ascending.
    The knee is the point of maximum perpendicular distance from the chord
    connecting the curve's two endpoints (kneedle-style), computed on the
    curve normalized to [0, 1] on both axes so the two very different
    scales (rank vs. distance) don't bias the geometry.

    Returns (eps, knee_percentile).
    """
    n = len(X_scaled)
    nn = NearestNeighbors(n_neighbors=k + 1)  # +1: a point is its own nearest neighbour at distance 0
    nn.fit(X_scaled)
    distances, _ = nn.kneighbors(X_scaled)
    k_dist_sorted = np.sort(distances[:, k])

    x = np.arange(n)
    x_norm = (x - x.min()) / (x.max() - x.min())
    y_norm = (k_dist_sorted - k_dist_sorted.min()) / (k_dist_sorted.max() - k_dist_sorted.min())
    x0, y0 = x_norm[0], y_norm[0]
    x1, y1 = x_norm[-1], y_norm[-1]
    num = np.abs((y1 - y0) * x_norm - (x1 - x0) * y_norm + x1 * y0 - y1 * x0)
    den = np.sqrt((y1 - y0) ** 2 + (x1 - x0) ** 2)
    knee_idx = int(np.argmax(num / den))

    eps = float(k_dist_sorted[knee_idx])
    knee_percentile = round(knee_idx / n * 100, 2)
    return eps, knee_percentile


def _fit_dbscan_at_knee(X_scaled: np.ndarray, min_samples: int = 8):
    """Fit DBSCAN once, with eps set directly to the k-distance knee (k=min_samples).

    Returns (db, labels, eps, knee_percentile).
    """
    eps, knee_percentile = _compute_knee_eps(X_scaled, k=min_samples)
    db = DBSCAN(eps=eps, min_samples=min_samples)
    labels = db.fit_predict(X_scaled)
    return db, labels, eps, knee_percentile


def run_clustering_pipeline(
    daily_profiles_path: Path,
    models_dir: Path,
    output_path: Path,
    k_min: int = 2,
    k_max: int = 12,
    dbscan_min_samples: int = 8,
) -> dict:
    """Cluster daily load profiles with KMeans (auto-selected k) and DBSCAN
    (eps set from the k-distance knee, computed at runtime -- see the
    module-level comment for why DBSCAN is expected to report a degenerate
    single-cluster result on this dataset).

    Saves:
        models_dir/kmeans_model.pkl
        models_dir/dbscan_model.pkl
        models_dir/profile_scaler.pkl
        models_dir/clustering_metrics.json
        output_path (cluster_results.csv)

    Returns dict with best_k, silhouette_score, davies_bouldin_score,
    total_days, dbscan_noise_days, cluster_counts, k_silhouette_scores,
    cluster_stats, and the dbscan_* diagnostic fields also written to
    clustering_metrics.json.
    """
    df = pd.read_csv(daily_profiles_path)

    available = [c for c in PROFILE_COLS if c in df.columns]
    X = df[available].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    best_k, _, k_scores = _select_best_k(X_scaled, k_min, k_max)

    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=20)
    kmeans_labels = kmeans.fit_predict(X_scaled)

    db, dbscan_labels, dbscan_eps, dbscan_knee_percentile = _fit_dbscan_at_knee(
        X_scaled, min_samples=dbscan_min_samples
    )

    sil = silhouette_score(X_scaled, kmeans_labels)
    dbi = davies_bouldin_score(X_scaled, kmeans_labels)

    models_dir.mkdir(parents=True, exist_ok=True)
    with open(models_dir / "kmeans_model.pkl", "wb") as f:
        pickle.dump(kmeans, f)
    with open(models_dir / "dbscan_model.pkl", "wb") as f:
        pickle.dump(db, f)
    with open(models_dir / "profile_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    result_df = pd.DataFrame(
        {"date": df["date"], "kmeans_cluster": kmeans_labels, "dbscan_cluster": dbscan_labels}
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)

    unique, counts = np.unique(kmeans_labels, return_counts=True)
    cluster_counts = {int(k): int(v) for k, v in zip(unique, counts)}

    # Per-cluster peak demand stats
    df_result = df.copy()
    df_result["kmeans_cluster"] = kmeans_labels
    cluster_stats = {}
    for cid in sorted(df_result["kmeans_cluster"].unique()):
        sub = df_result[df_result["kmeans_cluster"] == cid]
        cluster_stats[int(cid)] = {
            "count": int(len(sub)),
            "mean_peak_demand": round(float(sub["peak_demand"].mean()), 2),
            "mean_avg_demand": round(float(sub["mean_demand"].mean()), 2),
        }

    # DBSCAN diagnostics -- reported honestly, not tuned to look better.
    dbscan_noise_mask = dbscan_labels == -1
    dbscan_noise_count = int(np.sum(dbscan_noise_mask))
    dbscan_unique_clusters = sorted(set(dbscan_labels) - {-1})
    dbscan_n_clusters = len(dbscan_unique_clusters)
    dbscan_cluster_distribution = {
        int(c): int(np.sum(dbscan_labels == c)) for c in dbscan_unique_clusters
    }
    dbscan_largest_cluster_size = max(dbscan_cluster_distribution.values(), default=0)

    dbscan_non_noise_mask = ~dbscan_noise_mask
    dbscan_non_noise_count = int(np.sum(dbscan_non_noise_mask))
    if dbscan_n_clusters >= 2 and dbscan_non_noise_count > dbscan_n_clusters:
        dbscan_silhouette = round(
            float(silhouette_score(X_scaled[dbscan_non_noise_mask], dbscan_labels[dbscan_non_noise_mask])),
            4,
        )
    else:
        dbscan_silhouette = None

    if dbscan_n_clusters == 0:
        dbscan_status = "degenerate - no clusters (all noise)"
    elif dbscan_n_clusters == 1:
        dbscan_status = "degenerate - single cluster"
    else:
        dbscan_status = "ok"

    clustering_metrics = {
        "best_k": int(best_k),
        "silhouette_score": round(float(sil), 4),
        "davies_bouldin_index": round(float(dbi), 4),
        "cluster_distribution": {str(k): v for k, v in cluster_counts.items()},
        "dbscan_eps": round(dbscan_eps, 4),
        "dbscan_min_samples": dbscan_min_samples,
        "dbscan_knee_percentile": dbscan_knee_percentile,
        "dbscan_noise_count": dbscan_noise_count,
        "dbscan_n_clusters": dbscan_n_clusters,
        "dbscan_cluster_distribution": {str(k): v for k, v in dbscan_cluster_distribution.items()},
        "dbscan_largest_cluster_size": dbscan_largest_cluster_size,
        "dbscan_silhouette": dbscan_silhouette,
        "dbscan_status": dbscan_status,
        "k_silhouette_scores": k_scores,
    }
    with open(models_dir / "clustering_metrics.json", "w") as f:
        json.dump(clustering_metrics, f, indent=2)

    return {
        "best_k": int(best_k),
        "silhouette_score": round(float(sil), 4),
        "davies_bouldin_score": round(float(dbi), 4),
        "total_days": len(df),
        "dbscan_noise_days": dbscan_noise_count,
        "dbscan_eps": round(dbscan_eps, 4),
        "dbscan_min_samples": dbscan_min_samples,
        "dbscan_knee_percentile": dbscan_knee_percentile,
        "dbscan_n_clusters": dbscan_n_clusters,
        "dbscan_largest_cluster_size": dbscan_largest_cluster_size,
        "dbscan_silhouette": dbscan_silhouette,
        "dbscan_status": dbscan_status,
        "cluster_counts": cluster_counts,
        "k_silhouette_scores": k_scores,
        "cluster_stats": cluster_stats,
    }
