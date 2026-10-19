from pathlib import Path

import pandas as pd

from app.ml.behavior_labeling import LABEL_ABNORMAL, LABEL_LOW, LABEL_NORMAL, LABEL_PEAK

ALL_LABELS = [LABEL_ABNORMAL, LABEL_PEAK, LABEL_LOW, LABEL_NORMAL]

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

RISK_MAP = {
    LABEL_ABNORMAL: "High",
    LABEL_PEAK: "Medium",
    LABEL_LOW: "Low",
    LABEL_NORMAL: "Normal",
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

    The predicted label is the most frequent label among the matched days.
    Its raw frequency (e.g. 22 of 22 days = 100%) overstates certainty when
    few days match, so the displayed probabilities use Laplace (add-one)
    smoothing over the four labels: (count + 1) / (matched_days + 4).
    Example: 22 of 22 matched days -> 23 / 26 = 88.5%.

    Returns dict with:
        predicted_label, confidence_percent (smoothed likelihood of the
        predicted label), likelihood_percent (same value), raw_frequency_percent,
        predicted_label_count, risk_level, matched_days_count, match_strategy,
        match_description, label_counts, raw_probability_distribution,
        probability_distribution (smoothed), smoothing, explanation
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
    match_description = f"{DAY_NAMES[target_dayofweek]}s in {MONTH_NAMES[target_month - 1]}"

    if len(matched) == 0:
        matched = df[df["date"].dt.month == target_month]
        match_strategy = "month only (relaxed)"
        match_description = f"days in {MONTH_NAMES[target_month - 1]}"

    if len(matched) == 0:
        matched = df
        match_strategy = "full history (no seasonal match)"
        match_description = "all historical days"

    label_counts = matched["behavior_label"].value_counts()
    total_matched = len(matched)

    predicted_label = label_counts.idxmax()
    predicted_count = int(label_counts.max())
    raw_frequency = round(predicted_count / total_matched * 100, 2)

    counts = {label: int(label_counts.get(label, 0)) for label in ALL_LABELS}
    raw_probability_distribution = {
        label: round(counts[label] / total_matched * 100, 2) for label in ALL_LABELS
    }
    # Laplace (add-one) smoothing over the 4 labels: never 100% from limited data
    k = len(ALL_LABELS)
    probability_distribution = {
        label: round((counts[label] + 1) / (total_matched + k) * 100, 2) for label in ALL_LABELS
    }
    likelihood = probability_distribution[predicted_label]

    risk_level = RISK_MAP.get(predicted_label, "Unknown")

    explanation = (
        f"Based on {total_matched} historical days matched via '{match_strategy}' "
        f"({match_description}), '{predicted_label}' appeared on {predicted_count} of "
        f"{total_matched} days ({raw_frequency}%). Smoothed likelihood: {likelihood}%."
    )

    return {
        "predicted_label": predicted_label,
        "confidence_percent": likelihood,
        "likelihood_percent": likelihood,
        "raw_frequency_percent": raw_frequency,
        "predicted_label_count": predicted_count,
        "risk_level": risk_level,
        "matched_days_count": total_matched,
        "match_strategy": match_strategy,
        "match_description": match_description,
        "label_counts": counts,
        "raw_probability_distribution": raw_probability_distribution,
        "probability_distribution": probability_distribution,
        "smoothing": "Laplace (add-one) over 4 labels: (count + 1) / (matched_days + 4)",
        "explanation": explanation,
    }
