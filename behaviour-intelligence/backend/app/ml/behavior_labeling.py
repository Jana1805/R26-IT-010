import pandas as pd

# Label names describe what the rules actually detect on this data: the
# low-demand rule catches low-level days (all weekends here; the dataset has
# no holidays), and the default label applies to weekdays and weekends alike.
LABEL_ABNORMAL = "Abnormal Demand Day"
LABEL_PEAK = "Peak Demand Day"
LABEL_LOW = "Low Demand Day"
LABEL_NORMAL = "Normal Demand Day"


def generate_behavior_labels_from_csv(peak_demand_results_path, output_path) -> dict:
    """Assign a behaviour label to each day based on anomaly, peak, and low-demand rules.

    Priority order:
        1. Abnormal Demand Day — final_is_anomaly AND NOT is_peak_demand_day  | Risk: High
        2. Peak Demand Day     — is_peak_demand_day                           | Risk: Medium
        3. Low Demand Day      — mean_demand < 25th percentile                | Risk: Low
        4. Normal Demand Day   — all others                                   | Risk: Normal

    Adds columns: behavior_label, behavior_reason, behavior_risk_level
    Saves behavior_labels.csv.

    Returns dict with total_days, label_counts, label_percentages, low_demand_threshold.
    """
    from pathlib import Path

    peak_demand_results_path = Path(peak_demand_results_path)
    output_path = Path(output_path)

    df = pd.read_csv(peak_demand_results_path)
    low_threshold = df["mean_demand"].quantile(0.25)

    labels, reasons, risks = [], [], []

    for _, row in df.iterrows():
        is_anomaly = bool(row["final_is_anomaly"])
        is_peak = bool(row["is_peak_demand_day"])
        is_low = row["mean_demand"] < low_threshold

        if is_anomaly and not is_peak:
            label = LABEL_ABNORMAL
            risk = "High"
            reason = (
                f"Flagged as anomaly (iso_score={row['isolation_anomaly_score']:.3f}, "
                f"peak_zscore={row['peak_zscore']:.2f}) but not a peak day"
            )
        elif is_peak:
            label = LABEL_PEAK
            risk = "Medium"
            reason = f"Peak day triggered: {row.get('peak_reason', 'peak conditions met')}"
        elif is_low:
            label = LABEL_LOW
            risk = "Low"
            reason = (
                f"mean_demand ({row['mean_demand']:.1f} kW) < "
                f"25th percentile threshold ({low_threshold:.1f} kW)"
            )
        else:
            label = LABEL_NORMAL
            risk = "Normal"
            reason = (
                f"No anomaly, not a peak day, mean_demand ({row['mean_demand']:.1f} kW) "
                f">= low-demand threshold ({low_threshold:.1f} kW)"
            )

        labels.append(label)
        reasons.append(reason)
        risks.append(risk)

    df["behavior_label"] = labels
    df["behavior_reason"] = reasons
    df["behavior_risk_level"] = risks

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    total = len(df)
    counts = df["behavior_label"].value_counts().to_dict()
    percentages = {k: round(v / total * 100, 2) for k, v in counts.items()}

    risk_counts = df["behavior_risk_level"].value_counts().to_dict()

    return {
        "total_days": total,
        "label_counts": counts,
        "label_percentages": percentages,
        "low_demand_threshold": round(float(low_threshold), 2),
        "risk_distribution": risk_counts,
    }
