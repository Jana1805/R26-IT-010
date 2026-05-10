import pandas as pd


def remove_obvious_invalid_values(df: pd.DataFrame, demand_col: str) -> pd.DataFrame:
    """Drop rows with NaN or negative demand values."""
    df = df.dropna(subset=[demand_col])
    df = df[df[demand_col] >= 0].copy()
    return df.reset_index(drop=True)


def remove_extreme_spikes(df: pd.DataFrame, demand_col: str) -> pd.DataFrame:
    """Remove values above median + 10 * IQR."""
    q1 = df[demand_col].quantile(0.25)
    q3 = df[demand_col].quantile(0.75)
    iqr = q3 - q1
    upper_bound = df[demand_col].median() + 10 * iqr
    df = df[df[demand_col] <= upper_bound].copy()
    return df.reset_index(drop=True)


def fill_missing_values(df: pd.DataFrame, demand_col: str) -> pd.DataFrame:
    """Fill gaps by linear interpolation in both directions, then ffill/bfill."""
    df[demand_col] = df[demand_col].interpolate(method="linear", limit_direction="both")
    df[demand_col] = df[demand_col].ffill().bfill()
    return df


def remove_outliers_iqr(df: pd.DataFrame, demand_col: str, factor: float = 3.0) -> pd.DataFrame:
    """Remove values beyond factor * IQR from Q1/Q3."""
    q1 = df[demand_col].quantile(0.25)
    q3 = df[demand_col].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    df = df[(df[demand_col] >= lower) & (df[demand_col] <= upper)].copy()
    return df.reset_index(drop=True)


def resample_to_15min(df: pd.DataFrame, ts_col: str, demand_col: str) -> pd.DataFrame:
    """Resample the time series to 15-minute intervals using mean aggregation."""
    df = df.set_index(ts_col)
    df = df[[demand_col]].resample("15min").mean()
    df[demand_col] = df[demand_col].interpolate(method="linear", limit_direction="both")
    df = df.reset_index()
    df.columns = ["Timestamp", "Load Demand (kW)"]
    return df


def add_helper_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add Date (date only), Hour (int), and TimeSlot (0-95) columns."""
    df = df.copy()
    df["Date"] = df["Timestamp"].dt.date
    df["Hour"] = df["Timestamp"].dt.hour
    minute = df["Timestamp"].dt.minute
    df["TimeSlot"] = df["Hour"] * 4 + (minute // 15)
    return df


def preprocess_timeseries(df: pd.DataFrame, ts_col: str, demand_col: str) -> pd.DataFrame:
    """Run the full cleaning pipeline: remove invalids, spikes, fill gaps, remove outliers,
    resample to 15-min intervals, and attach helper columns."""
    df = remove_obvious_invalid_values(df, demand_col)
    df = remove_extreme_spikes(df, demand_col)
    df = fill_missing_values(df, demand_col)
    df = remove_outliers_iqr(df, demand_col)
    df = resample_to_15min(df, ts_col, demand_col)
    df = add_helper_columns(df)
    return df
