from pathlib import Path
from typing import Tuple

import pandas as pd

# Explicit column names to avoid auto-detection bugs
DEMAND_COLUMN = "Load Demand (kW)"
TIMESTAMP_COLUMN = "Timestamp"


def load_raw_dataset(filepath: Path) -> Tuple[pd.DataFrame, str, str]:
    """Load the raw CSV, parse timestamp and demand columns, and sort.

    Returns:
        (df, ts_col_name, demand_col_name)
    """
    df = pd.read_csv(filepath)

    # Use explicit column names instead of auto-detection
    ts_col = TIMESTAMP_COLUMN
    demand_col = DEMAND_COLUMN

    if ts_col not in df.columns:
        raise ValueError(f"Timestamp column '{ts_col}' not found. Available columns: {list(df.columns)}")
    if demand_col not in df.columns:
        raise ValueError(f"Demand column '{demand_col}' not found. Available columns: {list(df.columns)}")

    # pandas >= 2 infers a consistent format by default; infer_datetime_format
    # is deprecated (same parsed result on synthetic_realistic_load.csv).
    df[ts_col] = pd.to_datetime(df[ts_col], dayfirst=False)
    df[demand_col] = pd.to_numeric(df[demand_col], errors="coerce")
    df = df.sort_values(ts_col).reset_index(drop=True)

    return df, ts_col, demand_col
