from pathlib import Path
from typing import Tuple

import pandas as pd


def load_raw_dataset(filepath: Path) -> Tuple[pd.DataFrame, str, str]:
    """Load the raw CSV, auto-detect Timestamp and Load Demand columns, parse, and sort.

    Returns:
        (df, ts_col_name, demand_col_name)
    """
    df = pd.read_csv(filepath)

    col_lower = {col.lower(): col for col in df.columns}

    ts_col = None
    for key, col in col_lower.items():
        if "timestamp" in key or "time" in key or "date" in key:
            ts_col = col
            break

    demand_col = None
    for key, col in col_lower.items():
        if "load" in key or "demand" in key:
            demand_col = col
            break

    if ts_col is None:
        raise ValueError(f"No timestamp column found. Available columns: {list(df.columns)}")
    if demand_col is None:
        raise ValueError(f"No demand column found. Available columns: {list(df.columns)}")

    df[ts_col] = pd.to_datetime(df[ts_col], dayfirst=False, infer_datetime_format=True)
    df[demand_col] = pd.to_numeric(df[demand_col], errors="coerce")
    df = df.sort_values(ts_col).reset_index(drop=True)

    return df, ts_col, demand_col
