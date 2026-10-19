"""
Model Comparison Module for Behaviour Intelligence

This module compares multiple clustering algorithms on the same dataset
and provides structured comparison data for the frontend.

Algorithms compared:
- K-Means
- DBSCAN
- Agglomerative Clustering (Ward linkage)
- Gaussian Mixture Model

Metrics calculated:
- Silhouette Score (higher is better)
- Davies-Bouldin Index (lower is better)
- Calinski-Harabasz Index (higher is better)
- Number of clusters
- Noise points (for DBSCAN)

Ranking is by mean of per-metric ranks across Silhouette, Davies-Bouldin,
and Calinski-Harabasz -- not Silhouette alone. On this dataset, Gaussian
Mixture has the highest Silhouette (0.6558) but the worst Davies-Bouldin
(2.9566) and worst Calinski-Harabasz (58.46) of the three rankable models;
a Silhouette-only ranking would select it despite that. DBSCAN's eps is
computed from the k-distance knee via app.ml.clustering._compute_knee_eps,
matching clustering.py so the dashboard and this comparison page agree
(eps=4.4183). DBSCAN produces a single cluster on this dataset (see
clustering.py's module comment for the full sweep evidence) and is
excluded from the ranking rather than forced into a rank against metrics
it doesn't have.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from app.ml.clustering import _compute_knee_eps

PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]
CACHE_FILENAME = "model_comparison_cache.json"


def _models_dir_for(daily_profiles_path: Path) -> Path:
    """Models directory, derived from daily_profiles_path's fixed project
    layout (<root>/data/processed/daily_profiles.csv -> <root>/models) so
    this module doesn't need a new models_dir parameter threaded through
    from the caller."""
    return Path(daily_profiles_path).resolve().parent.parent.parent / "models"


def _load_cache(cache_path: Path, daily_profiles_path: Path) -> Optional[Dict]:
    """Return the cached result dict if the cache file exists and is newer
    than daily_profiles.csv, else None. Never raises -- a missing,
    unreadable, or malformed cache file just falls through to a fresh
    computation."""
    try:
        if not cache_path.exists():
            return None
        if cache_path.stat().st_mtime <= Path(daily_profiles_path).stat().st_mtime:
            return None
        with open(cache_path, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def _write_cache(cache_path: Path, result: Dict) -> None:
    """Best-effort cache write. Never raises -- a failed write must not
    break the endpoint."""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass


def _load_and_scale_data(daily_profiles_path: Path) -> Tuple[np.ndarray, StandardScaler]:
    """Load daily profiles and return scaled features and scaler."""
    df = pd.read_csv(daily_profiles_path)
    available = [c for c in PROFILE_COLS if c in df.columns]
    X = df[available].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, scaler


def _run_kmeans(X_scaled: np.ndarray, n_clusters: int = 2) -> Dict:
    """Run K-Means clustering and return metrics."""
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    labels = model.fit_predict(X_scaled)

    # Calculate metrics
    sil_score = silhouette_score(X_scaled, labels)
    dbi = davies_bouldin_score(X_scaled, labels)
    ch_score = calinski_harabasz_score(X_scaled, labels)

    # Cluster distribution
    unique, counts = np.unique(labels, return_counts=True)
    cluster_dist = {int(k): int(v) for k, v in zip(unique, counts)}

    return {
        "model_name": "K-Means",
        "model_type": "Partitioning",
        "description": "Iterative clustering algorithm that minimizes within-cluster variance",
        "n_clusters": n_clusters,
        "silhouette_score": round(float(sil_score), 4),
        "davies_bouldin_index": round(float(dbi), 4),
        "calinski_harabasz_score": round(float(ch_score), 4),
        "noise_points": 0,
        "cluster_distribution": cluster_dist,
    }


def _run_dbscan(X_scaled: np.ndarray, min_samples: int = 8) -> Dict:
    """Run DBSCAN with eps set from the k-distance knee (same method as
    clustering.py, so both pages agree). Reports silhouette,
    davies_bouldin, and calinski_harabasz as None -- not 0.0 -- when the
    result has fewer than 2 clusters, since those metrics are undefined
    in that case, not legitimately zero.
    """
    eps, knee_percentile = _compute_knee_eps(X_scaled, k=min_samples)
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(X_scaled)

    unique_labels = np.unique(labels)
    n_clusters = len(unique_labels[unique_labels != -1])
    noise_count = int(np.sum(labels == -1))

    if n_clusters >= 2:
        mask = labels != -1
        sil_score = round(float(silhouette_score(X_scaled[mask], labels[mask])), 4)
        dbi = round(float(davies_bouldin_score(X_scaled[mask], labels[mask])), 4)
        ch_score = round(float(calinski_harabasz_score(X_scaled[mask], labels[mask])), 4)
    else:
        sil_score = None
        dbi = None
        ch_score = None

    # Cluster distribution
    unique, counts = np.unique(labels, return_counts=True)
    cluster_dist = {int(k): int(v) for k, v in zip(unique, counts)}

    return {
        "model_name": "DBSCAN",
        "model_type": "Density-Based",
        "description": "Density-based clustering that identifies clusters of arbitrary shape",
        "n_clusters": n_clusters,
        "silhouette_score": sil_score,
        "davies_bouldin_index": dbi,
        "calinski_harabasz_score": ch_score,
        "noise_points": noise_count,
        "cluster_distribution": cluster_dist,
        "eps": round(eps, 4),
        "knee_percentile": knee_percentile,
    }


def _run_agglomerative(X_scaled: np.ndarray, n_clusters: int = 2) -> Dict:
    """Run Agglomerative Clustering (Ward linkage) and return metrics."""
    model = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
    labels = model.fit_predict(X_scaled)

    # Calculate metrics
    sil_score = silhouette_score(X_scaled, labels)
    dbi = davies_bouldin_score(X_scaled, labels)
    ch_score = calinski_harabasz_score(X_scaled, labels)

    # Cluster distribution
    unique, counts = np.unique(labels, return_counts=True)
    cluster_dist = {int(k): int(v) for k, v in zip(unique, counts)}

    return {
        "model_name": "Agglomerative Clustering",
        "model_type": "Hierarchical",
        "description": "Hierarchical clustering using Ward linkage to minimize variance",
        "n_clusters": n_clusters,
        "silhouette_score": round(float(sil_score), 4),
        "davies_bouldin_index": round(float(dbi), 4),
        "calinski_harabasz_score": round(float(ch_score), 4),
        "noise_points": 0,
        "cluster_distribution": cluster_dist,
    }


def _run_gaussian_mixture(X_scaled: np.ndarray, n_components: int = 2) -> Dict:
    """Run Gaussian Mixture Model and return metrics."""
    model = GaussianMixture(n_components=n_components, random_state=42)
    labels = model.fit_predict(X_scaled)

    # Calculate metrics
    sil_score = silhouette_score(X_scaled, labels)
    dbi = davies_bouldin_score(X_scaled, labels)
    ch_score = calinski_harabasz_score(X_scaled, labels)

    # Cluster distribution
    unique, counts = np.unique(labels, return_counts=True)
    cluster_dist = {int(k): int(v) for k, v in zip(unique, counts)}

    return {
        "model_name": "Gaussian Mixture Model",
        "model_type": "Probabilistic",
        "description": "Probabilistic model assuming clusters follow Gaussian distributions",
        "n_clusters": n_components,
        "silhouette_score": round(float(sil_score), 4),
        "davies_bouldin_index": round(float(dbi), 4),
        "calinski_harabasz_score": round(float(ch_score), 4),
        "noise_points": 0,
        "cluster_distribution": cluster_dist,
    }


def _rank_models(results: List[Dict]) -> List[Dict]:
    """Rank models by mean of per-metric ranks across Silhouette (higher
    better), Davies-Bouldin (lower better), and Calinski-Harabasz (higher
    better). Models with undefined metrics (fewer than 2 clusters -- e.g.
    DBSCAN's expected single-cluster result on this dataset) are excluded
    from the ranking rather than forced into a numeric rank against
    metrics they don't have.
    """
    rankable = [r for r in results if r["silhouette_score"] is not None]
    not_rankable = [r for r in results if r["silhouette_score"] is None]

    sil_order = sorted(rankable, key=lambda r: -r["silhouette_score"])
    dbi_order = sorted(rankable, key=lambda r: r["davies_bouldin_index"])
    ch_order = sorted(rankable, key=lambda r: -r["calinski_harabasz_score"])

    sil_rank = {r["model_name"]: i + 1 for i, r in enumerate(sil_order)}
    dbi_rank = {r["model_name"]: i + 1 for i, r in enumerate(dbi_order)}
    ch_rank = {r["model_name"]: i + 1 for i, r in enumerate(ch_order)}

    for r in rankable:
        r["silhouette_rank"] = sil_rank[r["model_name"]]
        r["davies_bouldin_rank"] = dbi_rank[r["model_name"]]
        r["calinski_harabasz_rank"] = ch_rank[r["model_name"]]
        r["mean_rank"] = round(
            (r["silhouette_rank"] + r["davies_bouldin_rank"] + r["calinski_harabasz_rank"]) / 3, 3
        )

    ranked = sorted(rankable, key=lambda r: r["mean_rank"])
    for rank, result in enumerate(ranked, 1):
        result["rank"] = rank
        result["status"] = "Best Model" if rank == 1 else "Alternative"

    for r in not_rankable:
        r["silhouette_rank"] = None
        r["davies_bouldin_rank"] = None
        r["calinski_harabasz_rank"] = None
        r["mean_rank"] = None
        r["rank"] = None
        r["status"] = "Not applicable - single cluster"

    return ranked + not_rankable


def _generate_explanation(best_model: Dict, all_results: List[Dict]) -> str:
    """Generate a clear explanation for why the best model was selected,
    based on mean rank across Silhouette, Davies-Bouldin, and
    Calinski-Harabasz -- not any single metric."""
    model_name = best_model["model_name"]
    ranked = sorted([r for r in all_results if r.get("rank") is not None], key=lambda r: r["rank"])
    n_ranked = len(ranked)

    explanation = (
        f"{model_name} ranks best overall (mean rank={best_model['mean_rank']}) across Silhouette "
        f"(rank {best_model['silhouette_rank']}), Davies-Bouldin (rank {best_model['davies_bouldin_rank']}), "
        f"and Calinski-Harabasz (rank {best_model['calinski_harabasz_rank']}) combined. It is not the top "
        f"performer on any single metric, but is consistently near the top across all three."
    )

    sil_winner = next((r for r in ranked if r["silhouette_rank"] == 1), None)
    if sil_winner and sil_winner["model_name"] != model_name:
        is_worst_dbi = sil_winner["davies_bouldin_rank"] == n_ranked
        is_worst_ch = sil_winner["calinski_harabasz_rank"] == n_ranked
        if is_worst_dbi and is_worst_ch:
            explanation += (
                f" {sil_winner['model_name']} has the highest Silhouette Score "
                f"({sil_winner['silhouette_score']}) of any model, but the worst Davies-Bouldin Index "
                f"({sil_winner['davies_bouldin_index']}) and worst Calinski-Harabasz Score "
                f"({sil_winner['calinski_harabasz_score']}) -- a Silhouette-only ranking would have "
                f"selected it despite that."
            )
        else:
            explanation += (
                f" {sil_winner['model_name']} has the highest Silhouette Score "
                f"({sil_winner['silhouette_score']}) of any model but ranked lower overall once "
                f"Davies-Bouldin and Calinski-Harabasz are included."
            )

    if best_model["noise_points"] > 0:
        explanation += f" It identified {best_model['noise_points']} noise points."

    return explanation


def _generate_summary_points(best_model: Dict) -> List[str]:
    """Generate bullet points summarizing why the best model is good."""
    points = []

    if best_model.get("mean_rank") is not None:
        points.append(
            f"Best mean rank ({best_model['mean_rank']}) across Silhouette (rank "
            f"{best_model['silhouette_rank']}), Davies-Bouldin (rank {best_model['davies_bouldin_rank']}), "
            f"and Calinski-Harabasz (rank {best_model['calinski_harabasz_rank']})"
        )

    # Silhouette score
    if best_model["silhouette_score"] > 0.5:
        points.append(f"Strong Silhouette Score ({best_model['silhouette_score']}) indicating well-separated clusters")
    elif best_model["silhouette_score"] > 0.3:
        points.append(f"Good Silhouette Score ({best_model['silhouette_score']}) indicating reasonable cluster separation")
    else:
        points.append(f"Silhouette Score ({best_model['silhouette_score']}) indicates moderate cluster separation")

    # Davies-Bouldin
    if best_model["davies_bouldin_index"] is not None:
        if best_model["davies_bouldin_index"] < 1.0:
            points.append(f"Competitive Davies-Bouldin Index ({best_model['davies_bouldin_index']}) indicating compact clusters")
        else:
            points.append(f"Reasonable Davies-Bouldin Index ({best_model['davies_bouldin_index']})")

    # Cluster distribution
    cluster_dist = best_model["cluster_distribution"]
    if len(cluster_dist) >= 2:
        points.append(f"Produces {len(cluster_dist)} meaningful clusters with balanced distribution")

    # Model-specific
    if best_model["model_type"] == "Partitioning":
        points.append("Efficient and scalable for large datasets")
    elif best_model["model_type"] == "Density-Based":
        points.append("Effective at identifying clusters of arbitrary shape")
    elif best_model["model_type"] == "Hierarchical":
        points.append("Provides interpretable cluster hierarchy")
    elif best_model["model_type"] == "Probabilistic":
        points.append("Provides probabilistic cluster assignments")

    return points


def run_clustering_model_comparison(
    daily_profiles_path: Path,
    n_clusters: int = 2,
    force_refresh: bool = False,
) -> Dict:
    """Run model comparison across multiple clustering algorithms.

    The result is cached to models/model_comparison_cache.json. A cached
    result is reused when the cache file is newer than daily_profiles.csv;
    otherwise it's recomputed and the cache is refreshed. Pass
    force_refresh=True to skip the cache read unconditionally. A missing/
    unreadable/malformed cache file or a failed cache write never breaks
    this call -- both are best-effort.

    Args:
        daily_profiles_path: Path to daily_profiles.csv
        n_clusters: Number of clusters for algorithms that require K
        force_refresh: Skip the cache read and recompute unconditionally

    Returns:
        Dict with comparison results including:
        - models: List of model results with metrics, per-metric ranks, and mean_rank
        - best_model: The best performing model by mean rank
        - explanation: Why the best model was selected
        - summary_points: Bullet points about the best model
        - comparison_table: Structured data for comparison table
        - cached: whether this response was served from the cache file
        - computed_at: ISO timestamp of when the underlying computation actually ran
    """
    daily_profiles_path = Path(daily_profiles_path)
    cache_path = _models_dir_for(daily_profiles_path) / CACHE_FILENAME

    if not force_refresh:
        cached_result = _load_cache(cache_path, daily_profiles_path)
        if cached_result is not None:
            cached_result = dict(cached_result)
            cached_result["cached"] = True
            return cached_result

    # Load and scale data
    X_scaled, _ = _load_and_scale_data(daily_profiles_path)

    # Run all models
    results = [
        _run_kmeans(X_scaled, n_clusters),
        _run_dbscan(X_scaled),
        _run_agglomerative(X_scaled, n_clusters),
        _run_gaussian_mixture(X_scaled, n_clusters),
    ]

    # Rank models
    ranked_results = _rank_models(results)

    # Get best model
    best_model = ranked_results[0]

    # Generate explanation
    explanation = _generate_explanation(best_model, ranked_results)

    # Generate summary points
    summary_points = _generate_summary_points(best_model)

    # Build comparison table data
    comparison_table = []
    for result in ranked_results:
        comparison_table.append({
            "model": result["model_name"],
            "silhouette_score": result["silhouette_score"] if result["silhouette_score"] is not None else "N/A",
            "davies_bouldin_index": result["davies_bouldin_index"] if result["davies_bouldin_index"] is not None else "N/A",
            "calinski_harabasz_score": result["calinski_harabasz_score"] if result["calinski_harabasz_score"] is not None else "N/A",
            "silhouette_rank": result["silhouette_rank"],
            "davies_bouldin_rank": result["davies_bouldin_rank"],
            "calinski_harabasz_rank": result["calinski_harabasz_rank"],
            "mean_rank": result["mean_rank"] if result["mean_rank"] is not None else "N/A",
            "n_clusters": result["n_clusters"],
            "noise_points": result["noise_points"],
            "rank": result["rank"],
            "status": result["status"],
        })

    result = {
        "models": ranked_results,
        "best_model": best_model,
        "explanation": explanation,
        "summary_points": summary_points,
        "comparison_table": comparison_table,
        "total_days": len(X_scaled),
        "cached": False,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    _write_cache(cache_path, result)

    return result
