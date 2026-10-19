"""Split-conformal calibration + performance data.

Uses ONLY the held-out test rows (never seen in training), split in two halves:
  calibration half -> residual distribution and the conformal interval width
  evaluation half  -> empirical coverage check of those intervals
Writes backend/saved_models/conformal.json and backend/saved_models/performance.json
Usage: venv/bin/python scripts/calibrate.py   (after train_model.py)
"""
import json, joblib, numpy as np, pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "backend" / "saved_models"
meta = json.load(open(M / "model_metadata.json")); F = meta["feature_names"]; T = meta["target_column"]
df = pd.read_csv(ROOT / "notebooks" / "load_forecasting_dataset_corrected.csv")
model = joblib.load(M / "forecast_model.pkl")
_, Xte, _, yte = train_test_split(df[F], df[T], test_size=0.2, random_state=42)  # same split as train_model.py
Xcal, Xev, ycal, yev = train_test_split(Xte, yte, test_size=0.5, random_state=7)

res_cal = (ycal - model.predict(Xcal)).to_numpy()
n = len(res_cal)
out = {"n_calibration": n, "n_evaluation": len(yev), "levels": {}}
pev = model.predict(Xev); rev = (yev.to_numpy() - pev)
for conf in (0.8, 0.9, 0.95):
    q = float(np.quantile(np.abs(res_cal), min(1.0, np.ceil((n + 1) * conf) / n)))  # finite-sample corrected
    cover = float(np.mean(np.abs(rev) <= q))
    out["levels"][str(conf)] = {"half_width_kw": q, "empirical_coverage": cover}
    print(f"{int(conf*100)}% interval: +/-{q:.1f} kW, empirical coverage {cover*100:.1f}%")
qs = np.linspace(0, 1, 1001)
out["residual_quantiles"] = np.quantile(res_cal, qs).round(2).tolist()  # empirical residual distribution for risk
json.dump(out, open(M / "conformal.json", "w"))

# performance tab data
rng = np.random.default_rng(1); idx = rng.choice(len(yev), 500, replace=False)
hist, edges = np.histogram(rev, bins=30)
perf = {
    "metrics": meta["model_performance"], "comparison": meta["model_comparison"], "importances": meta["feature_importances"],
    "scatter": [{"actual": float(yev.iloc[i]), "predicted": float(pev[i])} for i in idx],
    "error_hist": [{"from": float(edges[i]), "to": float(edges[i + 1]), "count": int(hist[i])} for i in range(len(hist))],
    "error_mean": float(rev.mean()), "error_std": float(rev.std()),
    "coverage": out["levels"],
    "by_hour": [{"hour": int(h), "mae": float(np.abs(rev[(Xev["Hour of Day"] == h).to_numpy()]).mean())} for h in range(24)],
    "evaluation_rows": len(yev),
}
json.dump(perf, open(M / "performance.json", "w"))
print("evaluation R2 on held-out half:", round(r2_score(yev, pev), 4), "MAE", round(mean_absolute_error(yev, pev), 1))
