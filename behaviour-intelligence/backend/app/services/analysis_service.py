import pandas as pd

from app.core.config import DATA_PROCESSED_DIR
from app.ml.behavior_labeling import LABEL_ABNORMAL, LABEL_LOW, LABEL_NORMAL, LABEL_PEAK
from app.ml.cluster_interpretation import interpret_clusters

_ALL_LABELS = [LABEL_NORMAL, LABEL_PEAK, LABEL_ABNORMAL, LABEL_LOW]

ANOMALY_LABEL_NOTE = (
    "Abnormal = anomaly days that are not peak days; anomaly days with high peaks "
    "are labelled Peak."
)
_ALL_RISKS = ["Normal", "Medium", "High", "Low"]
_PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]


def get_dashboard_summary() -> dict:
    """Read behavior_labels.csv and build the full dashboard KPI payload.

    Raises FileNotFoundError if the pipeline has not been run yet.
    """
    labels_path = DATA_PROCESSED_DIR / "behavior_labels.csv"
    if not labels_path.exists():
        raise FileNotFoundError(
            "Pipeline has not been run yet. Please run all 5 pipeline steps first."
        )

    df = pd.read_csv(labels_path)
    total = len(df)

    normal_days = int((df["behavior_label"] == LABEL_NORMAL).sum())
    peak_days = int((df["behavior_label"] == LABEL_PEAK).sum())
    abnormal_days = int((df["behavior_label"] == LABEL_ABNORMAL).sum())
    low_days = int((df["behavior_label"] == LABEL_LOW).sum())
    # Every Isolation Forest anomaly, whichever label it ended up with
    detected_anomaly_days = int(df["final_is_anomaly"].astype(bool).sum())
    anomaly_days_labelled_peak = int(
        (df["final_is_anomaly"].astype(bool) & (df["behavior_label"] == LABEL_PEAK)).sum()
    )

    label_distribution = [
        {
            "label": label,
            "count": int((df["behavior_label"] == label).sum()),
            "percentage": round(int((df["behavior_label"] == label).sum()) / total * 100, 2),
        }
        for label in _ALL_LABELS
    ]

    risk_distribution = [
        {"risk": risk, "count": int((df["behavior_risk_level"] == risk).sum())}
        for risk in _ALL_RISKS
    ]

    abnormal_cols = [
        "date", "peak_demand", "mean_demand",
        "behavior_reason", "behavior_risk_level", "isolation_anomaly_score",
    ]
    available_abnormal = [c for c in abnormal_cols if c in df.columns]
    recent_abnormal_days = (
        df[df["behavior_label"] == "Abnormal Demand Day"]
        .tail(10)[available_abnormal]
        .to_dict("records")
    )

    all_days_cols = [
        "date", "behavior_label", "behavior_risk_level",
        "peak_demand", "mean_demand",
        "kmeans_cluster", "dbscan_cluster",
        "isolation_anomaly_score", "peak_zscore", "peak_zscore_signed",
    ]
    available_all = [c for c in all_days_cols if c in df.columns]
    all_days = df[available_all].to_dict("records")

    cluster_interpretation = interpret_clusters(
        DATA_PROCESSED_DIR / "daily_profiles.csv",
        DATA_PROCESSED_DIR / "clustering_results.csv",
        DATA_PROCESSED_DIR / "anomaly_results.csv",
    )

    return {
        "total_days": total,
        "normal_days": normal_days,
        "peak_days": peak_days,
        "abnormal_days": abnormal_days,
        "low_days": low_days,
        "detected_anomaly_days": detected_anomaly_days,
        "anomaly_days_labelled_peak": anomaly_days_labelled_peak,
        "anomaly_label_note": ANOMALY_LABEL_NOTE,
        "cluster_interpretation": cluster_interpretation,
        "label_distribution": label_distribution,
        "risk_distribution": risk_distribution,
        "recent_abnormal_days": recent_abnormal_days,
        "all_days": all_days,
    }


def get_day_profile(date_str: str) -> dict:
    """Return the 96-slot load profile and behaviour metadata for a single date.

    Raises ValueError if the date is not found in daily_profiles.csv.
    """
    profiles_df = pd.read_csv(DATA_PROCESSED_DIR / "daily_profiles.csv")
    labels_df = pd.read_csv(DATA_PROCESSED_DIR / "behavior_labels.csv")

    profile_row = profiles_df[profiles_df["date"] == date_str]
    if profile_row.empty:
        raise ValueError(f"No profile found for date: {date_str}")

    label_row = labels_df[labels_df["date"] == date_str]

    available_profile_cols = [c for c in _PROFILE_COLS if c in profiles_df.columns]
    slot_values = profile_row[available_profile_cols].iloc[0].tolist()

    profile_points = []
    for slot, value in enumerate(slot_values):
        hour = slot // 4
        minute = (slot % 4) * 15
        profile_points.append(
            {"time_label": f"{hour:02d}:{minute:02d}", "slot": slot, "value": round(float(value), 2)}
        )

    behavior_label = label_row["behavior_label"].iloc[0] if not label_row.empty else "Unknown"
    behavior_risk = label_row["behavior_risk_level"].iloc[0] if not label_row.empty else "Unknown"
    behavior_reason = label_row["behavior_reason"].iloc[0] if not label_row.empty else ""

    return {
        "date": date_str,
        "profile_points": profile_points,
        "peak_demand": round(float(profile_row["peak_demand"].iloc[0]), 2),
        "mean_demand": round(float(profile_row["mean_demand"].iloc[0]), 2),
        "behavior_label": behavior_label,
        "behavior_risk_level": behavior_risk,
        "behavior_reason": behavior_reason,
    }
