"""Feature engineering functions used by model loading and forecasting."""

import numpy as np
import pandas as pd

from api.core.config import TARGET_COL
from api.utils.sanitizers import safe_float


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create temporal, lag, and rolling features required by the model."""
    df = df.copy()
    # The bundled CSV was exported with replacement characters in two unit labels.
    # Normalize them to the exact UTF-8 names recorded by the finalized notebooks.
    df.rename(columns={"Temperature (�C)": "Temperature (°C)",
                       "Solar Irradiance (W/m�)": "Solar Irradiance (W/m²)"}, inplace=True)

    df["sin_hour"] = np.sin(2 * np.pi * df["Hour of Day"] / 24)
    df["cos_hour"] = np.cos(2 * np.pi * df["Hour of Day"] / 24)
    df["sin_dow"] = np.sin(2 * np.pi * df["Day of Week"] / 7)
    df["cos_dow"] = np.cos(2 * np.pi * df["Day of Week"] / 7)
    df["sin_month"] = np.sin(2 * np.pi * df["Month"] / 12)
    df["cos_month"] = np.cos(2 * np.pi * df["Month"] / 12)

    df["is_weekend"] = (df["Day of Week"] >= 5).astype(int)
    df["year_norm"] = (df.index.year - 2022) / 3

    df["load_lag_96"] = df[TARGET_COL].shift(96)
    df["load_lag_192"] = df[TARGET_COL].shift(192)
    df["load_lag_672"] = df[TARGET_COL].shift(672)

    df["load_mean_week"] = df[TARGET_COL].shift(96).rolling(96 * 7).mean()
    df["load_std_day"] = df[TARGET_COL].shift(96).rolling(96).std()

    df.dropna(inplace=True)
    return df


def create_autoreg_row(
    next_ts: pd.Timestamp,
    mean_kw: float,
    anchor_idx: int,
    step_i: int,
    real_target: pd.Series,
    prev_row: pd.Series,
) -> pd.DataFrame:
    """Build one synthetic next-row for auto-regressive forecasting."""
    nr = prev_row.to_frame().T.copy()
    nr.index = [next_ts]
    nr[TARGET_COL] = mean_kw

    nr["sin_hour"] = np.sin(2 * np.pi * next_ts.hour / 24)
    nr["cos_hour"] = np.cos(2 * np.pi * next_ts.hour / 24)
    nr["sin_dow"] = np.sin(2 * np.pi * next_ts.dayofweek / 7)
    nr["cos_dow"] = np.cos(2 * np.pi * next_ts.dayofweek / 7)
    nr["sin_month"] = np.sin(2 * np.pi * next_ts.month / 12)
    nr["cos_month"] = np.cos(2 * np.pi * next_ts.month / 12)

    nr["is_weekend"] = int(next_ts.dayofweek >= 5)
    nr["year_norm"] = (next_ts.year - 2022) / 3

    lag_96_idx = anchor_idx - 96 + step_i + 1
    lag_192_idx = anchor_idx - 192 + step_i + 1
    lag_672_idx = anchor_idx - 672 + step_i + 1

    nr["load_lag_96"] = (
        safe_float(real_target.iloc[lag_96_idx], mean_kw) if lag_96_idx >= 0 else mean_kw
    )
    nr["load_lag_192"] = (
        safe_float(real_target.iloc[lag_192_idx], mean_kw) if lag_192_idx >= 0 else mean_kw
    )
    nr["load_lag_672"] = (
        safe_float(real_target.iloc[lag_672_idx], mean_kw) if lag_672_idx >= 0 else mean_kw
    )

    roll_end = lag_96_idx
    roll_week = max(0, roll_end - 96 * 7)
    roll_day = max(0, roll_end - 96)

    nr["load_mean_week"] = safe_float(
        real_target.iloc[roll_week:roll_end].mean() if roll_end > roll_week else mean_kw,
        mean_kw,
    )
    nr["load_std_day"] = safe_float(
        real_target.iloc[roll_day:roll_end].std() if roll_end > roll_day else 0.0,
        0.0,
    )

    return nr
