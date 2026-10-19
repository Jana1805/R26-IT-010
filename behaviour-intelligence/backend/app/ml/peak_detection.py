import pandas as pd
from scipy import stats

PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]

# The z-rule must use the SIGNED z-score of peak_demand. anomaly_results.csv's
# peak_zscore column is |z| (a diagnostic), and using it here labelled the 69
# days with the LOWEST daily peaks as "Peak Demand Day". A signed z > 2.0 only
# catches unusually HIGH peaks.
PEAK_Z_THRESHOLD = 2.0


def detect_peak_days(
    daily_profiles_path,
    anomaly_results_path,
    output_path,
) -> dict:
    """Identify peak demand days using percentile thresholds and anomaly signals.

    A day is flagged as a peak demand day when ANY of these conditions hold:
        - peak_demand >= 90th percentile
        - signed z-score of peak_demand > 2.0 (unusually HIGH peak only)
        - final_is_anomaly AND peak_demand >= 75th percentile

    Saves peak_demand_results.csv with added columns:
        peak_zscore_signed, is_peak_demand_day, peak_reason,
        threshold_90th_percentile, threshold_75th_percentile

    Returns dict with total_days, peak_days, non_peak_days,
    threshold_90th_percentile, threshold_75th_percentile.
    """
    from pathlib import Path

    daily_profiles_path = Path(daily_profiles_path)
    anomaly_results_path = Path(anomaly_results_path)
    output_path = Path(output_path)

    profiles_df = pd.read_csv(daily_profiles_path)
    anomaly_df = pd.read_csv(anomaly_results_path)

    available = [c for c in PROFILE_COLS if c in profiles_df.columns]
    df = anomaly_df.merge(profiles_df[["date"] + available], on="date", how="left")

    threshold_90 = df["peak_demand"].quantile(0.90)
    threshold_75 = df["peak_demand"].quantile(0.75)

    # Same z-score as anomaly_detection.py's peak_zscore, but keeping the sign.
    df["peak_zscore_signed"] = stats.zscore(df["peak_demand"].values, nan_policy="omit")

    cond_90 = df["peak_demand"] >= threshold_90
    cond_zscore = df["peak_zscore_signed"] > PEAK_Z_THRESHOLD
    cond_anomaly_75 = df["final_is_anomaly"] & (df["peak_demand"] >= threshold_75)

    df["is_peak_demand_day"] = cond_90 | cond_zscore | cond_anomaly_75

    def _build_reason(row):
        parts = []
        if row["peak_demand"] >= threshold_90:
            parts.append(f"peak_demand >= 90th percentile ({threshold_90:.1f} kW)")
        if row["peak_zscore_signed"] > PEAK_Z_THRESHOLD:
            parts.append(f"peak z-score > {PEAK_Z_THRESHOLD} ({row['peak_zscore_signed']:.2f})")
        if row["final_is_anomaly"] and row["peak_demand"] >= threshold_75:
            parts.append(f"anomaly with peak_demand >= 75th percentile ({threshold_75:.1f} kW)")
        return "; ".join(parts) if parts else "not a peak day"

    df["peak_reason"] = df.apply(_build_reason, axis=1)
    df["threshold_90th_percentile"] = round(threshold_90, 2)
    df["threshold_75th_percentile"] = round(threshold_75, 2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    return {
        "total_days": len(df),
        "peak_days": int(df["is_peak_demand_day"].sum()),
        "peak_days_by_condition": {
            "peak_ge_p90": int(cond_90.sum()),
            "signed_z_gt_threshold": int(cond_zscore.sum()),
            "anomaly_and_peak_ge_p75": int(cond_anomaly_75.sum()),
        },
        "non_peak_days": int((~df["is_peak_demand_day"]).sum()),
        "threshold_90th_percentile": round(float(threshold_90), 2),
        "threshold_75th_percentile": round(float(threshold_75), 2),
    }
