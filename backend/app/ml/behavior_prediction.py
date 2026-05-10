from pathlib import Path

import pandas as pd

ALL_LABELS = [
    "Abnormal Demand Day",
    "Peak Demand Day",
    "Holiday / Low Demand Day",
    "Normal Weekday Demand",
]

RISK_MAP = {
    "Abnormal Demand Day": "High",
    "Peak Demand Day": "Medium",
    "Holiday / Low Demand Day": "Low",
    "Normal Weekday Demand": "Normal",
}


def predict_future_behavior(behavior_labels_path, target_date_str: str) -> dict:
    """Predict the behaviour label for a future date using historical patterns.

    Matching strategy (applied in order until matches are found):
        1. Same calendar month AND same day-of-week
        2. Same calendar month only
        3. Full history as a fallback

    Args:
        behavior_labels_path: path to behavior_labels.csv
        target_date_str: target date as a string (e.g. "2025-08-14")

    Returns dict with:
        predicted_label, confidence_percent, risk_level,
        matched_days_count, match_strategy,
        probability_distribution, explanation
    """
    behavior_labels_path = Path(behavior_labels_path)

    df = pd.read_csv(behavior_labels_path)
    df["date"] = pd.to_datetime(df["date"])

    target_date = pd.to_datetime(target_date_str)
    target_month = target_date.month
    target_dayofweek = target_date.dayofweek

    matched = df[
        (df["date"].dt.month == target_month) & (df["date"].dt.dayofweek == target_dayofweek)
    ]
    match_strategy = "month + day-of-week"

    if len(matched) == 0:
        matched = df[df["date"].dt.month == target_month]
        match_strategy = "month only (relaxed)"

    if len(matched) == 0:
        matched = df
        match_strategy = "full history (no seasonal match)"

    label_counts = matched["behavior_label"].value_counts()
    total_matched = len(matched)

    predicted_label = label_counts.idxmax()
    confidence = round(label_counts.max() / total_matched * 100, 2)

    probability_distribution = {
        label: round(label_counts.get(label, 0) / total_matched * 100, 2)
        for label in ALL_LABELS
    }

    risk_level = RISK_MAP.get(predicted_label, "Unknown")

    explanation = (
        f"Based on {total_matched} historical days matched via '{match_strategy}' "
        f"(month={target_month}, dayofweek={target_dayofweek}), "
        f"'{predicted_label}' appeared {label_counts.max()} times "
        f"({confidence}% of matched days)."
    )

    return {
        "predicted_label": predicted_label,
        "confidence_percent": confidence,
        "risk_level": risk_level,
        "matched_days_count": total_matched,
        "match_strategy": match_strategy,
        "probability_distribution": probability_distribution,
        "explanation": explanation,
    }
