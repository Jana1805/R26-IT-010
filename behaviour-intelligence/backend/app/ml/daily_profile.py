import pandas as pd


def to_daily_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Convert preprocessed 15-minute time series into daily 96-slot load profiles.

    Only days that have readings for all 96 slots are kept.

    Returns DataFrame with columns:
        date, p00..p95, peak_demand, mean_demand, std_demand
    """
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    pivot = df.pivot_table(
        index="Date",
        columns="TimeSlot",
        values="Load Demand (kW)",
        aggfunc="mean",
    )

    # Require all 96 slots to be present
    pivot = pivot.dropna(thresh=96)

    # Guarantee exact columns 0..95 (fills any still-missing slot with NaN)
    pivot = pivot.reindex(columns=list(range(96)))

    rename_map = {i: f"p{str(i).zfill(2)}" for i in range(96)}
    pivot = pivot.rename(columns=rename_map)
    pivot = pivot.reset_index().rename(columns={"Date": "date"})

    profile_cols = [f"p{str(i).zfill(2)}" for i in range(96)]
    pivot["peak_demand"] = pivot[profile_cols].max(axis=1)
    pivot["mean_demand"] = pivot[profile_cols].mean(axis=1)
    pivot["std_demand"] = pivot[profile_cols].std(axis=1)

    pivot["date"] = pivot["date"].dt.strftime("%Y-%m-%d")
    return pivot
