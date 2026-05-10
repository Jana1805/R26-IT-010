import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]


def _select_best_k(X_scaled: np.ndarray, k_min: int = 2, k_max: int = 10):
    """Try KMeans for each k in [k_min, k_max] and return (best_k, best_silhouette_score)."""
    best_k = k_min
    best_score = -1.0
    for k in range(k_min, k_max + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        if score > best_score:
            best_score = score
            best_k = k
    return best_k, best_score


def _fit_dbscan_with_fallback(
    X_scaled: np.ndarray, eps_start: float = 1.6, min_samples: int = 8
):
    """Fit DBSCAN, retrying with eps += 0.4 up to 10 times if all points are noise."""
    eps = eps_start
    db = None
    labels = None
    for _ in range(10):
        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(X_scaled)
        if not np.all(labels == -1):
            return db, labels
        eps += 0.4
    return db, labels


def run_clustering_pipeline(
    daily_profiles_path: Path,
    models_dir: Path,
    output_path: Path,
    k_min: int = 2,
    k_max: int = 10,
) -> dict:
    """Cluster daily load profiles with KMeans (auto-selected k) and DBSCAN.

    Saves:
        models_dir/kmeans_model.pkl
        models_dir/profile_scaler.pkl
        output_path (cluster_results.csv)

    Returns dict with best_k, silhouette_score, davies_bouldin_score,
    total_days, dbscan_noise_days, cluster_counts.
    """
    df = pd.read_csv(daily_profiles_path)

    available = [c for c in PROFILE_COLS if c in df.columns]
    X = df[available].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    best_k, _ = _select_best_k(X_scaled, k_min, k_max)

    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    kmeans_labels = kmeans.fit_predict(X_scaled)

    _, dbscan_labels = _fit_dbscan_with_fallback(X_scaled)

    sil = silhouette_score(X_scaled, kmeans_labels)
    dbi = davies_bouldin_score(X_scaled, kmeans_labels)

    models_dir.mkdir(parents=True, exist_ok=True)
    with open(models_dir / "kmeans_model.pkl", "wb") as f:
        pickle.dump(kmeans, f)
    with open(models_dir / "profile_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    result_df = pd.DataFrame(
        {"date": df["date"], "kmeans_cluster": kmeans_labels, "dbscan_cluster": dbscan_labels}
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)

    unique, counts = np.unique(kmeans_labels, return_counts=True)
    cluster_counts = {int(k): int(v) for k, v in zip(unique, counts)}

    return {
        "best_k": int(best_k),
        "silhouette_score": round(float(sil), 4),
        "davies_bouldin_score": round(float(dbi), 4),
        "total_days": len(df),
        "dbscan_noise_days": int(np.sum(dbscan_labels == -1)),
        "cluster_counts": cluster_counts,
    }
