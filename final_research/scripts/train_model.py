"""Train the deployed forecaster and write everything the API serves.

Writes: backend/saved_models/forecast_model.pkl, model_metadata.json, reference.json
        backend/outputs/scenario_results.json
Usage:  venv/bin/python scripts/train_model.py
"""
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import optuna
from sklearn.model_selection import KFold, cross_val_score, train_test_split

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "notebooks" / "load_forecasting_dataset_corrected.csv"
MODELS, OUTPUTS = ROOT / "backend" / "saved_models", ROOT / "backend" / "outputs"

FEATURES = ["Temperature (°C)", "Humidity (%)", "Wind Speed (m/s)", "Rainfall (mm)",
            "Solar Irradiance (W/m²)", "GDP (LKR)", "Per Capita Energy Use (kWh)",
            "Electricity Price (LKR/kWh)", "Day of Week", "Hour of Day", "Month",
            "Public Event", "Poya Day"]
TARGET = "Load Demand (kW)"

# ======================= CONFIGURATION: every parameter used below lives here =======================
SEED = 42
TEST_SIZE = 0.2                      # 80% train / 20% test
INITIAL_PARAMS = dict(n_estimators=300, max_depth=5, learning_rate=0.08, subsample=0.8)   # Gradient Boosting starting point
RF_PARAMS = dict(n_estimators=100, max_depth=10)
OPTUNA = dict(n_trials=20, cv_folds=3, search_rows=20_000, sampler_seed=42)               # tuning budget
# Optuna search space for Gradient Boosting (name: (low, high, kind))
SEARCH_SPACE = dict(
    n_estimators=(100, 300, "int-step50"), max_depth=(3, 7, "int"), learning_rate=(0.03, 0.2, "log-float"),
    subsample=(0.6, 1.0, "float"), min_samples_leaf=(5, 80, "log-int"), max_features=(0.5, 1.0, "float"))
# =====================================================================================================


def metrics(y, p):
    return dict(r2=float(r2_score(y, p)), mae=float(mean_absolute_error(y, p)),
                rmse=float(np.sqrt(mean_squared_error(y, p))))


df = pd.read_csv(DATA)
X, y = df[FEATURES], df[TARGET]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=TEST_SIZE, random_state=SEED)

# ---- Step 1: baseline comparison of three model families (initial parameters) -------------------------
candidates = {
    "Linear Regression": LinearRegression(),
    "Random Forest": RandomForestRegressor(random_state=SEED, n_jobs=-1, **RF_PARAMS),
    "Gradient Boosting": GradientBoostingRegressor(random_state=SEED, **INITIAL_PARAMS),
}
comparison = {}
for name, m in candidates.items():
    m.fit(Xtr, ytr)
    s_ = metrics(yte, m.predict(Xte))
    comparison[name] = dict(test_r2=s_["r2"], test_mae=s_["mae"], test_rmse=s_["rmse"])
    print(f"{name:20s} R2={s_['r2']:.4f} MAE={s_['mae']:.1f} RMSE={s_['rmse']:.1f}")
family = max(comparison, key=lambda n: comparison[n]["test_r2"])
assert family == "Gradient Boosting", "tuning below is written for Gradient Boosting"
print("best family:", family)

# ---- Step 2: Optuna tuning (training data only; the test set is never touched here) --------------------
optuna.logging.set_verbosity(optuna.logging.WARNING)
Xs = Xtr.sample(OPTUNA["search_rows"], random_state=SEED); ys = ytr.loc[Xs.index]       # subsample keeps the search fast
cv = KFold(n_splits=OPTUNA["cv_folds"], shuffle=True, random_state=SEED)

def cv_rmse(params):
    """Cross-validated RMSE of Gradient Boosting with these parameters (lower is better)."""
    scores = cross_val_score(GradientBoostingRegressor(random_state=SEED, **params), Xs, ys, cv=cv,
                             scoring="neg_root_mean_squared_error")
    return float(-scores.mean())

def suggest(trial):
    p = {}
    for k, (lo, hi, kind) in SEARCH_SPACE.items():
        if kind == "int-step50": p[k] = trial.suggest_int(k, lo, hi, step=50)
        elif kind == "int": p[k] = trial.suggest_int(k, lo, hi)
        elif kind == "log-int": p[k] = trial.suggest_int(k, lo, hi, log=True)
        elif kind == "log-float": p[k] = trial.suggest_float(k, lo, hi, log=True)
        else: p[k] = trial.suggest_float(k, lo, hi)
    return p

initial_cv = cv_rmse(INITIAL_PARAMS)
study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=OPTUNA["sampler_seed"]))
study.optimize(lambda t: cv_rmse(suggest(t)), n_trials=OPTUNA["n_trials"])
print(f"CV RMSE: initial {initial_cv:.2f} | best of {OPTUNA['n_trials']} trials {study.best_value:.2f}")
print("best params:", study.best_params)

# ---- Step 3: choose by CROSS-VALIDATION (not by test), then refit on the full training set -------------
use_tuned = study.best_value < initial_cv
final_params = {**INITIAL_PARAMS, **study.best_params} if use_tuned else dict(INITIAL_PARAMS)
model = GradientBoostingRegressor(random_state=SEED, **final_params).fit(Xtr, ytr)
tuned_name = "Gradient Boosting (Optuna-tuned)"
s_t = metrics(yte, model.predict(Xte))
comparison[tuned_name] = dict(test_r2=s_t["r2"], test_mae=s_t["mae"], test_rmse=s_t["rmse"])
print(f"{tuned_name}: R2={s_t['r2']:.4f} MAE={s_t['mae']:.1f} RMSE={s_t['rmse']:.1f}")
best = tuned_name if use_tuned else family
tr, te = metrics(ytr, model.predict(Xtr)), metrics(yte, model.predict(Xte))

# honest extra check: chronological split (train on first 80% of time, test on the last 20%)
cut = int(len(df) * 0.8)
chrono = GradientBoostingRegressor(random_state=SEED, **final_params).fit(X.iloc[:cut], y.iloc[:cut])
chrono_s = metrics(y.iloc[cut:], chrono.predict(X.iloc[cut:]))
print("deployed:", best, "| chronological test R2 =", round(chrono_s["r2"], 4))

joblib.dump(model, MODELS / "forecast_model.pkl")
importances = dict(zip(FEATURES, map(float, model.feature_importances_)))
meta = dict(
    model_type=type(model).__name__, feature_names=FEATURES, target_column=TARGET,
    model_performance=dict(train_r2=tr["r2"], test_r2=te["r2"], train_mae=tr["mae"], test_mae=te["mae"],
                           train_rmse=tr["rmse"], test_rmse=te["rmse"],
                           chronological_test_r2=chrono_s["r2"], chronological_test_mae=chrono_s["mae"]),
    model_comparison=comparison, feature_importances=importances,
    hyperparameters=final_params,
    optuna=dict(n_trials=OPTUNA["n_trials"], cv_folds=OPTUNA["cv_folds"], search_rows=OPTUNA["search_rows"],
                search_space={k: list(v) for k, v in SEARCH_SPACE.items()}, initial_params=INITIAL_PARAMS,
                initial_cv_rmse=initial_cv, best_cv_rmse=float(study.best_value), best_params=study.best_params,
                tuned_params_deployed=bool(use_tuned)),
    data_info=dict(total_samples=len(df), train_samples=len(Xtr), test_samples=len(Xte),
                   source="notebooks/load_forecasting_dataset_corrected.csv"),
    deployment_decision=(f"{best} deployed. Gradient Boosting was the best of three families on test R2; its parameters were then "
                         f"tuned with Optuna ({OPTUNA['n_trials']} trials, {OPTUNA['cv_folds']}-fold CV on training data only)"
                         + (" and the tuned parameters beat the initial ones in cross-validation." if use_tuned else
                            ", but the initial parameters were better in cross-validation and were kept.")),
)
json.dump(meta, open(MODELS / "model_metadata.json", "w"), indent=2)

# reference data for the UI: ranges, typical day, supply limit
num = [c for c in FEATURES if c not in ("Day of Week", "Hour of Day", "Month", "Public Event", "Poya Day")]
ranges = {c: dict(min=float(df[c].min()), p5=float(df[c].quantile(.05)), p95=float(df[c].quantile(.95)),
                  max=float(df[c].max()), mean=float(df[c].mean())) for c in num}
typical = {c: round(float(df[c].mean()), 2) for c in num}
typical.update({"Day of Week": 2, "Hour of Day": 19, "Month": 6, "Public Event": 0, "Poya Day": 0})
# default supply limit: 20% headroom over the peak of a typical day, so a normal day reads "Safe"
_day = pd.DataFrame([{**typical, "Hour of Day": h} for h in range(24)])[FEATURES]
cap = float(np.ceil(model.predict(_day).max() * 1.2 / 50) * 50)
json.dump(dict(ranges=ranges, typical=typical, features=FEATURES, default_capacity_kw=cap,
               demand_percentiles={str(q): float(df[TARGET].quantile(q / 100)) for q in (5, 25, 50, 75, 95, 99)}),
          open(MODELS / "reference.json", "w"), indent=2)

# keep the legacy /api/scenarios file populated
s = df.sample(1000, random_state=42)
def apply(d, k):
    d = d.copy()
    if k == "heat_wave": d["Temperature (°C)"] += 8; d["Humidity (%)"] = np.maximum(0, d["Humidity (%)"] - 15)
    if k == "cold_spell": d["Temperature (°C)"] = np.maximum(0, d["Temperature (°C)"] - 10); d["Humidity (%)"] = np.minimum(100, d["Humidity (%)"] + 20)
    if k == "price_shock": d["Electricity Price (LKR/kWh)"] *= 2
    if k == "economic_boom": d["GDP (LKR)"] *= 1.2; d["Per Capita Energy Use (kWh)"] *= 1.1
    return d
b = float(np.mean(model.predict(s[FEATURES]))); res = {}
for k in ["heat_wave", "cold_spell", "price_shock", "economic_boom"]:
    v = float(np.mean(model.predict(apply(s, k)[FEATURES])))
    res[k] = dict(baseline_demand=b, scenario_demand=v, absolute_change=v - b, percentage_change=(v - b) / b * 100)
    print(f"  {k:14s} {res[k]['percentage_change']:+.1f}%")
json.dump(dict(metadata=dict(baseline_samples=1000, model_type=meta["model_type"], features_count=len(FEATURES),
                             baseline_demand=b, model_performance=meta["model_performance"]), scenarios=res),
          open(OUTPUTS / "scenario_results.json", "w"), indent=2)
