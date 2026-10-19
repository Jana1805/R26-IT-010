"""Cross-dataset check behind DATASET_CHECK.md (workspace root).

Read-only on the data: reads the XAI dataset, the dataset Behaviour
Intelligence uses (synthetic_realistic_load.csv) and the neural-forecasting
dataset, plus the saved XGBoost hyperparameters. Writes only
backend/outputs/v2/dataset_check.json. The component itself keeps using
load_forecasting_dataset_corrected.csv.

    venv\Scripts\python.exe experiments\dataset_check.py
"""
import json, time, warnings
from pathlib import Path
import numpy as np, pandas as pd, joblib, shap, xgboost as xgb
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2].as_posix()   # workspace root
OUT = f"{ROOT}/madushani_xai/backend/outputs/v2/dataset_check.json"
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
DATASETS = {
    "xai_current": f"{ROOT}/behaviour-intelligence/data/raw/load_forecasting_dataset_corrected.csv",
    "bi_current":  f"{ROOT}/behaviour-intelligence/data/raw/synthetic_realistic_load.csv",
    "nn_fixed":    f"{ROOT}/electricity-demand-sri-lanka/data/electricity_demand_srilanka_fixed.csv",
}
T = "Load Demand (kW)"
XAI_COLS = ['Temperature (°C)', 'Humidity (%)', 'Wind Speed (m/s)', 'Rainfall (mm)',
            'Solar Irradiance (W/m²)', 'GDP (LKR)', 'Per Capita Energy Use (kWh)',
            'Electricity Price (LKR/kWh)', 'Day of Week', 'Hour of Day', 'Month', 'Public Event']
SHORT = dict(zip(XAI_COLS, ["Temperature", "Humidity", "Wind Speed", "Rainfall", "Solar Irradiance", "GDP",
                            "Per Capita Energy Use", "Electricity Price", "Day of Week", "Hour of Day", "Month", "Public Event"]))
best = joblib.load(f"{ROOT}/madushani_xai/backend/outputs/xgb_model.pkl").get_params()
BEST = {k: best[k] for k in ["n_estimators", "max_depth", "learning_rate", "subsample", "colsample_bytree",
                             "min_child_weight", "reg_alpha", "reg_lambda", "random_state"]}

def metrics(y, p):
    return {"rmse": float(np.sqrt(mean_squared_error(y, p))), "mae": float(mean_absolute_error(y, p)),
            "mape": float(np.mean(np.abs((y - p) / y)) * 100), "r2": float(r2_score(y, p))}

res = {"xgb_params": BEST}
raw_frames = {}
for name, path in DATASETS.items():
    t0 = time.time()
    df = pd.read_csv(path)
    r = {"path": path.replace(ROOT + "/", ""), "columns": list(df.columns), "rows": int(len(df))}
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values("Timestamp").reset_index(drop=True)
    step = df["Timestamp"].diff().dropna()
    expected = int((df["Timestamp"].max() - df["Timestamp"].min()) / pd.Timedelta("15min")) + 1
    r.update({
        "start": str(df["Timestamp"].min()), "end": str(df["Timestamp"].max()),
        "step_mode": str(step.mode().iloc[0]), "expected_15min_rows": expected,
        "missing_15min_slots": int(expected - df["Timestamp"].nunique()),
        "duplicate_timestamps": int(df["Timestamp"].duplicated().sum()),
        "missing_values": {c: int(v) for c, v in df.isna().sum().items() if v > 0},
        "target_stats": {k: round(float(v), 3) for k, v in df[T].describe().items()},
        "xai_features_present": [SHORT[c] for c in XAI_COLS if c in df.columns],
        "xai_features_missing": [SHORT[c] for c in XAI_COLS if c not in df.columns],
        "extra_columns": [c for c in df.columns if c not in XAI_COLS + ["Timestamp", T]],
    })
    # Calendar features derivable from the timestamp (needed for the BI file)
    df["Hour of Day d"] = df["Timestamp"].dt.hour
    df["Day of Week d"] = df["Timestamp"].dt.dayofweek
    df["Month d"] = df["Timestamp"].dt.month
    for c in ["Day of Week", "Hour of Day", "Month"]:
        if c in df.columns:
            r[f"{c}_matches_timestamp"] = bool((df[c] == df[f"{c} d"]).mean() > 0.999)
            r[f"{c}_match_rate"] = round(float((df[c] == df[f"{c} d"]).mean()), 4)
    feats = [c for c in XAI_COLS if c in df.columns]
    if "Hour of Day" not in df.columns:
        df["Hour of Day"], df["Day of Week"], df["Month"] = df["Hour of Day d"], df["Day of Week d"], df["Month d"]
        feats += ["Day of Week", "Hour of Day", "Month"]
        r["derived_from_timestamp"] = ["Day of Week", "Hour of Day", "Month"]
    r["model_features"] = [SHORT.get(c, c) for c in feats]

    # Correlation with target
    r["corr_with_target"] = {SHORT.get(c, c): round(float(df[c].corr(df[T])), 4) for c in feats}

    # Full-data linear fit: is the target a trivial linear function?
    lr = LinearRegression().fit(df[feats], df[T])
    resid = df[T] - lr.predict(df[feats])
    r["lr_full_fit"] = {"r2": float(r2_score(df[T], lr.predict(df[feats]))),
                        "max_abs_residual": float(np.abs(resid).max()), "resid_std": float(resid.std()),
                        "intercept": float(lr.intercept_),
                        "coefs": {SHORT.get(c, c): float(v) for c, v in zip(feats, lr.coef_)}}
    lr_t = LinearRegression().fit(df[[feats[0]]], df[T])
    r["lr_temperature_only_r2"] = float(r2_score(df[T], lr_t.predict(df[[feats[0]]])))

    # Same preprocessing as madushani_xai notebook 1: IQR on target, chrono 80/20
    q1, q3 = df[T].quantile(.25), df[T].quantile(.75); iqr = q3 - q1
    dc = df[(df[T] >= q1 - 1.5 * iqr) & (df[T] <= q3 + 1.5 * iqr)].reset_index(drop=True)
    split = int(len(dc) * .8)
    tr, te = dc.iloc[:split], dc.iloc[split:]
    Xtr, Xte = tr[feats].rename(columns=SHORT), te[feats].rename(columns=SHORT)
    ytr, yte = tr[T].values, te[T].values
    r["split"] = {"rows_after_iqr": int(len(dc)), "iqr_removed": int(len(df) - len(dc)),
                  "train": int(len(tr)), "test": int(len(te)),
                  "test_start": str(te["Timestamp"].iloc[0]), "test_end": str(te["Timestamp"].iloc[-1])}
    cmp = {}
    t1 = time.time(); lrm = LinearRegression().fit(Xtr, ytr)
    cmp["Linear Regression"] = {**metrics(yte, lrm.predict(Xte)), "train_s": round(time.time() - t1, 2)}
    # LR with one-hot hour / day-of-week / month: lets a linear model capture daily/weekly shape
    oh = lambda X: pd.get_dummies(X.astype({"Hour of Day": int, "Day of Week": int, "Month": int}),
                                  columns=["Hour of Day", "Day of Week", "Month"], dtype=float)
    Xtr_oh = oh(Xtr); Xte_oh = oh(Xte).reindex(columns=Xtr_oh.columns, fill_value=0)
    t1 = time.time(); lro = LinearRegression().fit(Xtr_oh, ytr)
    cmp["Linear Regression + one-hot calendar"] = {**metrics(yte, lro.predict(Xte_oh)), "train_s": round(time.time() - t1, 2)}
    t1 = time.time(); xm = xgb.XGBRegressor(**BEST).fit(Xtr, ytr)
    cmp["XGBoost (current best params)"] = {**metrics(yte, xm.predict(Xte)), "train_s": round(time.time() - t1, 2)}
    # Naive seasonal baseline: same 15-min slot one week earlier
    s = dc.set_index("Timestamp")[T]
    lag = s.shift(freq="7D").reindex(te["Timestamp"]).values
    ok = ~np.isnan(lag)
    cmp["Seasonal naive (same slot, 7 days earlier)"] = {**metrics(yte[ok], lag[ok]), "coverage": round(float(ok.mean()), 4)}
    r["model_comparison"] = cmp

    # Non-linear / calendar structure
    hr = df.groupby("Hour of Day d")[T].mean(); dw = df.groupby("Day of Week d")[T].mean()
    r["hourly_profile_kw"] = {int(k): round(float(v), 1) for k, v in hr.items()}
    r["hour_range_kw"] = round(float(hr.max() - hr.min()), 1)
    r["dow_profile_kw"] = {int(k): round(float(v), 1) for k, v in dw.items()}
    r["weekend_minus_weekday_kw"] = round(float(df.loc[df["Day of Week d"] >= 5, T].mean() - df.loc[df["Day of Week d"] < 5, T].mean()), 1)
    for ev in ["Public Event", "Poya Day"]:
        if ev in df.columns:
            r[f"{ev}_effect_kw"] = round(float(df.loc[df[ev] == 1, T].mean() - df.loc[df[ev] == 0, T].mean()), 1)
            r[f"{ev}_share"] = round(float((df[ev] == 1).mean()), 4)
    tc = feats[0]
    bins = df.groupby(df[tc].round().clip(df[tc].quantile(.005).round(), df[tc].quantile(.995).round()))[T].mean()
    r["temperature_curve_kw"] = {int(k): round(float(v), 1) for k, v in bins.items()}
    lin = np.polyfit(df[tc], df[T], 1); quad = np.polyfit(df[tc], df[T], 2)
    r["temp_linear_vs_quadratic_r2"] = [float(r2_score(df[T], np.polyval(lin, df[tc]))),
                                        float(r2_score(df[T], np.polyval(quad, df[tc])))]
    # Hour x temperature interaction: does the temperature slope change by hour?
    slopes = {}
    for h in [3, 9, 14, 19]:
        sub = df[df["Hour of Day d"] == h]
        slopes[h] = round(float(np.polyfit(sub[tc], sub[T], 1)[0]), 2)
    r["temp_slope_by_hour_kw_per_c"] = slopes

    # SHAP on 2,000 test rows of the XGBoost just trained
    smp = Xte.sample(min(2000, len(Xte)), random_state=42)
    sv = shap.TreeExplainer(xm).shap_values(smp)
    ma = dict(sorted({c: float(v) for c, v in zip(smp.columns, np.abs(sv).mean(0))}.items(), key=lambda x: -x[1]))
    tot = sum(ma.values())
    r["shap_mean_abs_kw"] = {k: round(v, 3) for k, v in ma.items()}
    r["shap_share_pct"] = {k: round(v / tot * 100, 2) for k, v in ma.items()}
    r["shap_features_over_5pct"] = [k for k, v in ma.items() if v / tot > .05]
    r["elapsed_s"] = round(time.time() - t0, 1)
    res[name] = r
    raw_frames[name] = df[["Timestamp", T]]
    print(f"done {name} in {r['elapsed_s']}s", flush=True)

# Do the same dates mean the same demand across files?
daily = {n: f.set_index("Timestamp")[T].resample("D").agg(["mean", "max"]) for n, f in raw_frames.items()}
pairs = {}
for a, b in [("xai_current", "bi_current"), ("nn_fixed", "bi_current"), ("xai_current", "nn_fixed")]:
    j = daily[a].join(daily[b], lsuffix="_a", rsuffix="_b", how="inner").dropna()
    pairs[f"{a}_vs_{b}"] = {"overlap_days": int(len(j)),
                            "daily_mean_corr": round(float(j["mean_a"].corr(j["mean_b"])), 4),
                            "daily_peak_corr": round(float(j["max_a"].corr(j["max_b"])), 4),
                            "mean_abs_peak_diff_kw": round(float((j["max_a"] - j["max_b"]).abs().mean()), 1)}
res["cross_dataset_dates"] = pairs
res["example_2025_01_25_daily_peak_kw"] = {n: round(float(d.loc["2025-01-25", "max"]), 2) if "2025-01-25" in d.index else None
                                           for n, d in daily.items()}
# Are BI's 60 anomaly dates inside each file's range?
an = pd.read_csv(f"{ROOT}/behaviour-intelligence/data/processed/anomaly_results.csv")
ad = pd.to_datetime(an.loc[an.final_is_anomaly.astype(bool), "date"]).dt.normalize()
res["bi_anomaly_dates_covered"] = {n: int(ad.isin(d.index).sum()) for n, d in daily.items()}
res["bi_anomaly_dates_total"] = int(len(ad))
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("saved", OUT)
