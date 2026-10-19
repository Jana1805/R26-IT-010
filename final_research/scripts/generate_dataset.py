"""Regenerate the synthetic `Load Demand (kW)` column with explainable structure.

Practice-work dataset: every feature column is kept exactly as in the
electricity-demand-sri-lanka data; only the target is regenerated as

    demand = f(features) + Gaussian noise

where f encodes simple, physically sensible rules (daily load shape, air-conditioning
load that grows with temperature and humidity, weekend / Poya / public-event dips,
mild price elasticity, GDP and per-capita growth, seasonal wobble). Noise is sized so a
tuned boosted model reaches a test R2 of roughly 0.8. This is a *designed* synthetic
signal, not a measurement - disclose that if the work is assessed.

Usage:  venv/bin/python scripts/generate_dataset.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "backup_original_dataset" / "janahan_fixed_unmodified.csv"
OUT = ROOT / "notebooks" / "load_forecasting_dataset_corrected.csv"
TARGET_R2 = 0.83  # approximate share of variance the features explain
SEED = 42

# relative daily load shape (index = hour 0..23), 1.0 = daily mean
HOUR_SHAPE = np.array([0.80, 0.77, 0.75, 0.74, 0.76, 0.82, 0.92, 1.02, 1.05, 1.00, 0.98, 0.98,
                       0.99, 0.98, 0.97, 0.98, 1.02, 1.12, 1.27, 1.30, 1.20, 1.07, 0.94, 0.85])


def demand_signal(d: pd.DataFrame) -> np.ndarray:
    t, h = d["Temperature (°C)"].to_numpy(), d["Humidity (%)"].to_numpy()
    hour = d["Hour of Day"].to_numpy().astype(int)
    base = 1500.0 * HOUR_SHAPE[hour]
    # cooling load: starts above ~26 C, amplified by humidity, strongest in afternoon/evening
    cooling_gain = 0.6 + 0.4 * np.clip((HOUR_SHAPE[hour] - 0.75) / 0.55, 0, 1)
    cooling = 40.0 * np.clip(t - 26.0, 0, None) * (1 + 0.012 * (h - 80)) * cooling_gain
    # mild heating / comfort-driven load when it is unusually cool
    cool = 6.0 * np.clip(22.0 - t, 0, None)
    mult = np.ones(len(d))
    mult *= (d["Electricity Price (LKR/kWh)"].to_numpy() / 25.0) ** -0.18        # price elasticity
    mult *= (d["GDP (LKR)"].to_numpy() / 1000.0) ** 0.40                          # economic activity
    mult *= (d["Per Capita Energy Use (kWh)"].to_numpy() / 500.0) ** 0.45        # household appetite
    mult *= np.where(d["Day of Week"].to_numpy() >= 5, 0.91, 1.0)                 # weekend dip
    mult *= np.where(d["Public Event"].to_numpy() == 1, 0.93, 1.0)
    mult *= np.where(d["Poya Day"].to_numpy() == 1, 0.90, 1.0)
    mult *= 1 + 0.03 * np.sin((d["Month"].to_numpy() - 3) / 12 * 2 * np.pi)       # seasonal wobble
    weather = 1 - 0.004 * d["Rainfall (mm)"].to_numpy() - 0.01 * d["Wind Speed (m/s)"].to_numpy()
    return (base + cooling + cool) * mult * weather


if __name__ == "__main__":
    df = pd.read_csv(SRC)
    f = demand_signal(df)
    sigma = np.sqrt(f.var() * (1 / TARGET_R2 - 1))
    rng = np.random.default_rng(SEED)
    df["Load Demand (kW)"] = np.clip(f + rng.normal(0, sigma, len(f)), 0, None).round(4)
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT}  rows={len(df)}  signal std={f.std():.1f}  noise sigma={sigma:.1f}")
