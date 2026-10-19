"""
Anomaly Detection Model Comparison Module for Behaviour Intelligence

This module compares multiple anomaly detection algorithms on the same dataset
and provides structured comparison data for the frontend.

Algorithms compared:
- Isolation Forest
- Z-Score (Statistical) — max(|z(peak_demand)|, |z(mean_demand)|), matching
  the production definition in anomaly_detection.py
- One-Class SVM
- Local Outlier Factor (LOF)

Models are ranked by bootstrap stability: how consistently each model's
flagged set survives resampling 80% of the days, over 20 fixed-seed
resamples. Isolation Forest, One-Class SVM, and LOF are all pre-tuned to a
~3% expected rate via contamination/nu, so flagged-set SIZE (and any metric
derived only from set size, e.g. rate-deviation or consensus-vote F1) is not
an independent quality signal — WHICH days keep getting flagged under
resampling is. Pairwise Spearman rank correlation between models' continuous
scores is reported separately as a diagnostic, not folded into the ranking.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from scipy import stats

PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]

N_RESAMPLES = 20
RESAMPLE_FRAC = 0.8
CONSENSUS_STATUS_NA = "Not applicable - flags no days"
CACHE_FILENAME = "anomaly_comparison_cache.json"


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


def _load_and_scale_data(daily_profiles_path: Path):
    """Load daily profiles and return scaled features."""
    df = pd.read_csv(daily_profiles_path)
    available = [c for c in PROFILE_COLS if c in df.columns]
    X = df[available].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, df


def _run_isolation_forest(X_scaled: np.ndarray, contamination: float = 0.03):
    """Run Isolation Forest. Returns (metrics, anomaly_flags, oriented_score).

    oriented_score is -decision_function, i.e. higher = more anomalous, for
    use in rank-correlation comparisons across models.
    """
    model = IsolationForest(
        n_estimators=300,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    predictions = model.fit_predict(X_scaled)
    decision_scores = model.decision_function(X_scaled)

    anomaly_flags = predictions == -1
    anomaly_count = int(np.sum(anomaly_flags))
    anomaly_percentage = round((anomaly_count / len(X_scaled)) * 100, 2)

    mean_score = round(float(np.mean(decision_scores)), 4)
    std_score = round(float(np.std(decision_scores)), 4)

    metrics = {
        "model_name": "Isolation Forest",
        "model_type": "Ensemble-based",
        "description": "Isolation-based anomaly detection using random forest",
        "anomaly_count": anomaly_count,
        "anomaly_percentage": anomaly_percentage,
        "mean_anomaly_score": mean_score,
        "std_anomaly_score": std_score,
        "contamination": contamination,
    }
    return metrics, anomaly_flags, -decision_scores


def _run_zscore(df: pd.DataFrame, threshold: float = 3.0):
    """Run Z-Score anomaly detection using the PRODUCTION definition:
    max(|z(peak_demand)|, |z(mean_demand)|) on the raw columns, matching
    anomaly_detection.py. Returns (metrics, anomaly_flags, oriented_score).
    """
    peak_z = np.abs(stats.zscore(df["peak_demand"].values, nan_policy="omit"))
    mean_z = np.abs(stats.zscore(df["mean_demand"].values, nan_policy="omit"))
    z_score = np.maximum(peak_z, mean_z)

    anomaly_flags = z_score >= threshold
    anomaly_count = int(np.sum(anomaly_flags))
    anomaly_percentage = round((anomaly_count / len(df)) * 100, 2)

    mean_zscore = round(float(np.mean(z_score)), 4)
    std_zscore = round(float(np.std(z_score)), 4)

    metrics = {
        "model_name": "Z-Score",
        "model_type": "Statistical",
        "description": "max(|z(peak_demand)|, |z(mean_demand)|) - matches anomaly_detection.py",
        "anomaly_count": anomaly_count,
        "anomaly_percentage": anomaly_percentage,
        "mean_anomaly_score": mean_zscore,
        "std_anomaly_score": std_zscore,
        "threshold": threshold,
    }
    return metrics, anomaly_flags, z_score


def _run_one_class_svm(X_scaled: np.ndarray, nu: float = 0.03):
    """Run One-Class SVM. Returns (metrics, anomaly_flags, oriented_score).

    Note: sklearn's OneClassSVM has no random_state parameter.
    """
    model = OneClassSVM(
        kernel='rbf',
        nu=nu,
        gamma='scale',
    )
    anomaly_scores = model.fit_predict(X_scaled)
    decision_scores = model.decision_function(X_scaled)

    anomaly_flags = anomaly_scores == -1
    anomaly_count = int(np.sum(anomaly_flags))
    anomaly_percentage = round((anomaly_count / len(X_scaled)) * 100, 2)

    mean_score = round(float(np.mean(decision_scores)), 4)
    std_score = round(float(np.std(decision_scores)), 4)

    metrics = {
        "model_name": "One-Class SVM",
        "model_type": "Support Vector Machine",
        "description": "Support vector machine for anomaly detection",
        "anomaly_count": anomaly_count,
        "anomaly_percentage": anomaly_percentage,
        "mean_anomaly_score": mean_score,
        "std_anomaly_score": std_score,
        "nu": nu,
    }
    return metrics, anomaly_flags, -decision_scores


def _run_lof(X_scaled: np.ndarray, contamination: float = 0.03):
    """Run Local Outlier Factor. Returns (metrics, anomaly_flags, oriented_score)."""
    model = LocalOutlierFactor(
        n_neighbors=20,
        contamination=contamination,
        n_jobs=-1
    )
    anomaly_scores = model.fit_predict(X_scaled)
    decision_scores = model.negative_outlier_factor_

    anomaly_flags = anomaly_scores == -1
    anomaly_count = int(np.sum(anomaly_flags))
    anomaly_percentage = round((anomaly_count / len(X_scaled)) * 100, 2)

    mean_score = round(float(np.mean(decision_scores)), 4)
    std_score = round(float(np.std(decision_scores)), 4)

    metrics = {
        "model_name": "Local Outlier Factor",
        "model_type": "Density-based",
        "description": "Local density-based outlier detection",
        "anomaly_count": anomaly_count,
        "anomaly_percentage": anomaly_percentage,
        "mean_anomaly_score": mean_score,
        "std_anomaly_score": std_score,
        "n_neighbors": 20,
    }
    return metrics, anomaly_flags, -decision_scores


def _pairwise_spearman(scores_by_model: Dict[str, np.ndarray]) -> Dict[str, Dict[str, float]]:
    """4x4 pairwise Spearman rank correlation between models' continuous scores.
    All scores must already be oriented higher = more anomalous."""
    names = list(scores_by_model.keys())
    matrix: Dict[str, Dict[str, float]] = {}
    for a in names:
        matrix[a] = {}
        for b in names:
            rho, _ = stats.spearmanr(scores_by_model[a], scores_by_model[b])
            matrix[a][b] = round(float(rho), 4)
    return matrix


def _bootstrap_stability(
    X_scaled: np.ndarray,
    df: pd.DataFrame,
    full_flagged: Dict[str, set],
    contamination: float,
    n_resamples: int,
    resample_frac: float,
) -> Dict[str, Dict[str, float]]:
    """For each model, resample resample_frac of days (without replacement,
    fixed seeds 0..n_resamples-1) n_resamples times and measure agreement
    between each resample's flagged set and the full-data flagged set.

    Reports mean/std Jaccard (set-size-normalized overlap) and mean symmetric
    difference (raw count of days that differ), since Jaccard can look
    identical across models whose flagged-set sizes are pinned by
    contamination even when the actual membership diverges.
    """
    n = len(X_scaled)
    sample_size = int(resample_frac * n)

    jaccards: Dict[str, List[float]] = {name: [] for name in full_flagged}
    sym_diffs: Dict[str, List[int]] = {name: [] for name in full_flagged}

    for seed in range(n_resamples):
        rng = np.random.default_rng(seed)
        sub_idx = np.sort(rng.choice(n, size=sample_size, replace=False))
        X_sub = X_scaled[sub_idx]
        df_sub = df.iloc[sub_idx].reset_index(drop=True)

        _, iso_flags, _ = _run_isolation_forest(X_sub, contamination)
        _, zscore_flags, _ = _run_zscore(df_sub)
        _, svm_flags, _ = _run_one_class_svm(X_sub, contamination)
        _, lof_flags, _ = _run_lof(X_sub, contamination)

        resample_flagged = {
            "Isolation Forest": set(sub_idx[iso_flags].tolist()),
            "Z-Score": set(sub_idx[zscore_flags].tolist()),
            "One-Class SVM": set(sub_idx[svm_flags].tolist()),
            "Local Outlier Factor": set(sub_idx[lof_flags].tolist()),
        }

        for name in full_flagged:
            a = resample_flagged[name]
            b = full_flagged[name]
            union = a | b
            jaccard = 0.0 if not union else len(a & b) / len(union)
            jaccards[name].append(jaccard)
            sym_diffs[name].append(len(a ^ b))

    stability = {}
    for name in full_flagged:
        j = np.array(jaccards[name])
        sd = np.array(sym_diffs[name])
        stability[name] = {
            "mean_jaccard": round(float(j.mean()), 4),
            "std_jaccard": round(float(j.std()), 4),
            "mean_symmetric_difference": round(float(sd.mean()), 2),
        }
    return stability


def _generate_explanation(
    best_model: Optional[Dict],
    not_applicable: List[Dict],
    n_resamples: int,
    resample_frac: float,
) -> str:
    """Explain why the best model was selected, or why no ranking could be made."""
    if best_model is None:
        return (
            "No model produced a rankable flagged set — every model either flags no days "
            "or has no stability signal to compare."
        )

    explanation = (
        f"{best_model['model_name']} was selected because its flagged set is the most stable "
        f"under resampling: mean Jaccard={best_model['mean_jaccard']} against the full-data "
        f"flagged set across {n_resamples} bootstrap resamples of {int(resample_frac * 100)}% "
        f"of days (mean symmetric difference={best_model['mean_symmetric_difference']} days)."
    )

    if best_model["model_type"] == "Ensemble-based":
        explanation += " It is robust to high-dimensional data and provides consistent results."
    elif best_model["model_type"] == "Statistical":
        explanation += " It is computationally efficient and easy to interpret."
    elif best_model["model_type"] == "Support Vector Machine":
        explanation += " It is effective for non-linear decision boundaries."
    elif best_model["model_type"] == "Density-based":
        explanation += " It is sensitive to local data density and can detect local anomalies."

    for result in not_applicable:
        if result["model_name"] == "Z-Score":
            explanation += (
                " Z-Score is excluded from ranking: it flags 0 days at threshold=3.0 on this "
                "dataset, so a stability score of 0.0 would reflect that it never fires in any "
                "resample, not that it is unstable."
            )

    return explanation


def _generate_summary_points(best_model: Dict, n_resamples: int) -> List[str]:
    """Generate bullet points summarizing why the best model is good."""
    points = []

    j = best_model["mean_jaccard"]
    if j >= 0.8:
        points.append(f"Mean Jaccard={j} across {n_resamples} resamples — strong stability under resampling")
    elif j >= 0.5:
        points.append(f"Mean Jaccard={j} across {n_resamples} resamples — moderate stability under resampling")
    else:
        points.append(f"Mean Jaccard={j} across {n_resamples} resamples — the most stable available, though still limited")

    points.append(
        f"Mean symmetric difference={best_model['mean_symmetric_difference']} days between "
        "each resample's flagged set and the full-data flagged set"
    )

    if best_model["model_type"] == "Ensemble-based":
        points.append("Robust ensemble method with proven reliability")
        points.append("Handles high-dimensional profile data effectively")
    elif best_model["model_type"] == "Statistical":
        points.append("Computationally efficient and fast")
        points.append("Easy to interpret and explain")
    elif best_model["model_type"] == "Support Vector Machine":
        points.append("Effective for complex non-linear patterns")
        points.append("Good generalization capability")
    elif best_model["model_type"] == "Density-based":
        points.append("Sensitive to local data density")
        points.append("Can detect local anomalies effectively")

    if best_model["std_anomaly_score"] < 1.0:
        points.append("Stable anomaly scores with low variance")

    return points


def run_anomaly_detection_comparison(
    daily_profiles_path: Path,
    contamination: float = 0.03,
    n_resamples: int = N_RESAMPLES,
    resample_frac: float = RESAMPLE_FRAC,
    force_refresh: bool = False,
) -> Dict:
    """Run model comparison across multiple anomaly detection algorithms.

    Ranking is by bootstrap stability (mean Jaccard between each of
    n_resamples fixed-seed resamples' flagged set and the full-data flagged
    set), not by anomaly rate or by agreement-based F1 — both of those
    collapse to a function of contamination/nu when 3 of the 4 models are
    pre-tuned to the same expected rate. Pairwise Spearman rank correlation
    on continuous scores is reported separately as a diagnostic.

    The result is cached to models/anomaly_comparison_cache.json (this is
    the ~11s bootstrap-resampling call). A cached result is reused when the
    cache file is newer than daily_profiles.csv; otherwise it's recomputed
    and the cache is refreshed. Pass force_refresh=True to skip the cache
    read unconditionally. A missing/unreadable/malformed cache file or a
    failed cache write never breaks this call -- both are best-effort.

    Args:
        daily_profiles_path: Path to daily_profiles.csv
        contamination: Contamination/nu passed to Isolation Forest, One-Class
            SVM, and LOF (reported per-model; not used for ranking)
        n_resamples: Number of bootstrap resamples (fixed seeds 0..n_resamples-1)
        resample_frac: Fraction of days sampled without replacement per resample
        force_refresh: Skip the cache read and recompute unconditionally

    Returns:
        Dict with comparison results including:
        - models: list of model result dicts (metrics + stability + rank/status)
        - best_model: the top-ranked model dict, or None if nothing is rankable
        - explanation: why the best model was selected
        - summary_points: bullet points about the best model
        - comparison_table: structured data for a comparison table
        - spearman_matrix: pairwise Spearman rank correlation (diagnostic only)
        - contamination_note: reminder that 3/4 models share a pinned expected rate
        - bootstrap_config: {n_resamples, resample_frac, seeds}
        - total_days: total days evaluated
        - runtime_seconds: wall-clock time for the original computation (unchanged on a cache hit)
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

    start_time = time.time()

    X_scaled, df = _load_and_scale_data(daily_profiles_path)

    iso_metrics, iso_flags, iso_score = _run_isolation_forest(X_scaled, contamination)
    zscore_metrics, zscore_flags, zscore_score = _run_zscore(df)
    svm_metrics, svm_flags, svm_score = _run_one_class_svm(X_scaled, contamination)
    lof_metrics, lof_flags, lof_score = _run_lof(X_scaled, contamination)

    metrics_by_model = {
        "Isolation Forest": iso_metrics,
        "Z-Score": zscore_metrics,
        "One-Class SVM": svm_metrics,
        "Local Outlier Factor": lof_metrics,
    }
    flags_by_model = {
        "Isolation Forest": iso_flags,
        "Z-Score": zscore_flags,
        "One-Class SVM": svm_flags,
        "Local Outlier Factor": lof_flags,
    }
    scores_by_model = {
        "Isolation Forest": iso_score,
        "Z-Score": zscore_score,
        "One-Class SVM": svm_score,
        "Local Outlier Factor": lof_score,
    }
    full_flagged = {name: set(np.where(flags)[0].tolist()) for name, flags in flags_by_model.items()}

    spearman_matrix = _pairwise_spearman(scores_by_model)
    stability = _bootstrap_stability(
        X_scaled, df, full_flagged, contamination, n_resamples, resample_frac
    )

    results = []
    for name, metrics in metrics_by_model.items():
        result = {**metrics, **stability[name]}
        if name == "Z-Score" and metrics["anomaly_count"] == 0:
            result["status"] = CONSENSUS_STATUS_NA
        results.append(result)

    applicable = [r for r in results if r.get("status") != CONSENSUS_STATUS_NA]
    not_applicable = [r for r in results if r.get("status") == CONSENSUS_STATUS_NA]

    ranked_applicable = sorted(applicable, key=lambda r: r["mean_jaccard"], reverse=True)
    for rank, result in enumerate(ranked_applicable, 1):
        result["rank"] = rank
        result["status"] = "Best Model" if rank == 1 else "Alternative"
    for result in not_applicable:
        result["rank"] = None

    ranked_results = ranked_applicable + not_applicable
    best_model = ranked_applicable[0] if ranked_applicable else None

    explanation = _generate_explanation(best_model, not_applicable, n_resamples, resample_frac)
    summary_points = _generate_summary_points(best_model, n_resamples) if best_model else []

    contamination_note = (
        "Isolation Forest, One-Class SVM, and Local Outlier Factor are all pre-tuned to an "
        f"expected anomaly rate of {contamination * 100:.0f}% (contamination/nu={contamination}), "
        "so flagged-set size alone is not an independent quality signal — the bootstrap stability "
        "ranking below measures agreement on WHICH days get flagged, not how many."
    )

    comparison_table = []
    for result in ranked_results:
        comparison_table.append({
            "model": result["model_name"],
            "anomaly_count": result["anomaly_count"],
            "anomaly_percentage": result["anomaly_percentage"],
            "mean_anomaly_score": result["mean_anomaly_score"],
            "std_anomaly_score": result["std_anomaly_score"],
            "mean_jaccard": result["mean_jaccard"],
            "std_jaccard": result["std_jaccard"],
            "mean_symmetric_difference": result["mean_symmetric_difference"],
            "rank": result["rank"],
            "status": result["status"],
        })

    runtime_seconds = round(time.time() - start_time, 2)

    result = {
        "models": ranked_results,
        "best_model": best_model,
        "explanation": explanation,
        "summary_points": summary_points,
        "comparison_table": comparison_table,
        "spearman_matrix": spearman_matrix,
        "contamination_note": contamination_note,
        "bootstrap_config": {
            "n_resamples": n_resamples,
            "resample_frac": resample_frac,
            "seeds": f"0-{n_resamples - 1}",
        },
        "total_days": len(df),
        "runtime_seconds": runtime_seconds,
        "cached": False,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    _write_cache(cache_path, result)

    return result
