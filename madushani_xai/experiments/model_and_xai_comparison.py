"""
Model and XAI comparison for the madushani_xai component (v2 evidence).

Reproduces, with fixed seeds:
  A. Forecasting-model comparison on the notebook-1 split (seasonal naive,
     Linear Regression, Optuna-tuned Random Forest, the deployed XGBoost),
     plus 5-fold rolling-origin cross-validation.
  B. SHAP TreeExplainer vs LIME on the deployed xgb_model.pkl, scored against
     the known ground truth of this dataset (Load = 100*T - 1300 exactly).
  C. Per-year SHAP of the ONE deployed model with bootstrap 95% CIs.
  D. Cross-dataset check (runs experiments/dataset_check.py).

It only READS the dataset and xgb_model.pkl. It never retrains or overwrites
xgb_model.pkl, temporal_drift.json or anomaly_diagnosis.json. Outputs go to
backend/outputs/v2/ (JSON) and backend/outputs/figures/ (PNG).

Run from anywhere with the component venv:
    venv\\Scripts\\python.exe experiments\\model_and_xai_comparison.py            # all parts
    venv\\Scripts\\python.exe experiments\\model_and_xai_comparison.py --parts B,C
"""
import argparse
import json
import runpy
import time
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
import shap
import xgboost as xgb
from lime.lime_tabular import LimeTabularExplainer
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

SEED = 42
HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
WORKSPACE = COMPONENT.parent
DATASET = WORKSPACE / "behaviour-intelligence" / "data" / "raw" / "load_forecasting_dataset_corrected.csv"
MODEL_PATH = COMPONENT / "backend" / "outputs" / "xgb_model.pkl"
OUT_V2 = COMPONENT / "backend" / "outputs" / "v2"
FIG_DIR = COMPONENT / "backend" / "outputs" / "figures"

TARGET = "Load Demand (kW)"
FEATURE_COLS = [
    "Temperature (°C)", "Humidity (%)", "Wind Speed (m/s)", "Rainfall (mm)",
    "Solar Irradiance (W/m²)", "GDP (LKR)", "Per Capita Energy Use (kWh)",
    "Electricity Price (LKR/kWh)", "Day of Week", "Hour of Day", "Month", "Public Event",
]
FEATURES = [
    "Temperature", "Humidity", "Wind Speed", "Rainfall", "Solar Irradiance",
    "GDP", "Per Capita Energy Use", "Electricity Price",
    "Day of Week", "Hour of Day", "Month", "Public Event",
]
LEVELS = ["low", "medium", "high", "peak"]

# Figure style: dark surface matching the dashboard cards. Categorical slots
# validated with the dataviz validator against #0C1828 (all checks pass).
SURFACE, TEXT, TEXT_2, GRID = "#0C1828", "#E2E8F0", "#94A3B8", "#1E2D42"
C_SHAP, C_LIME, C_THIRD = "#3987e5", "#d95926", "#199e70"
C_POS, C_NEG = "#3987e5", "#e66767"   # diverging pair for signed weights
plt.rcParams.update({"axes.titlecolor": TEXT, "text.color": TEXT})


# ── helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def to_py(o):
    """Recursively convert numpy types so json.dump works."""
    if isinstance(o, dict):
        return {str(k): to_py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_py(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if np.isnan(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return to_py(o.tolist())
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


def save_json(obj, name):
    OUT_V2.mkdir(parents=True, exist_ok=True)
    path = OUT_V2 / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_py(obj), f, indent=2, ensure_ascii=False)
    log(f"saved {path.relative_to(COMPONENT)}")


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y, p))),
        "mae": float(mean_absolute_error(y, p)),
        "mape": float(np.mean(np.abs((y - p) / y)) * 100),
        "r2": float(r2_score(y, p)),
    }


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.xaxis.label.set_color(TEXT_2)
    ax.yaxis.label.set_color(TEXT_2)
    ax.title.set_color(TEXT)
    ax.grid(color=GRID, linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)


def new_fig(w=8, h=4.5, nrows=1, ncols=1, **kw):
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h), facecolor=SURFACE, **kw)
    for ax in np.atleast_1d(axes).ravel():
        style_axes(ax)
    return fig, axes


def save_fig(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, dpi=130, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    log(f"saved {path.relative_to(COMPONENT)}")
    return name


def load_data():
    """Same cleaning and split as notebooks/1_shap_temporal_drift.ipynb."""
    df = pd.read_csv(DATASET)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values("Timestamp").reset_index(drop=True)
    q1, q3 = df[TARGET].quantile(0.25), df[TARGET].quantile(0.75)
    iqr = q3 - q1
    clean = df[(df[TARGET] >= q1 - 1.5 * iqr) & (df[TARGET] <= q3 + 1.5 * iqr)].copy().reset_index(drop=True)
    split = int(len(clean) * 0.80)
    X = clean[FEATURE_COLS].copy()
    X.columns = FEATURES
    y = clean[TARGET].reset_index(drop=True)
    return {
        "raw": df, "clean": clean, "X": X, "y": y, "split": split,
        "X_train": X.iloc[:split], "y_train": y.iloc[:split],
        "X_test": X.iloc[split:], "y_test": y.iloc[split:],
        "ts_test": clean["Timestamp"].iloc[split:],
    }


def inference_ms_per_1000(predict, X, repeats=3):
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        predict(X)
        best = min(best, time.perf_counter() - t0)
    return best / len(X) * 1000 * 1000


# ── Part A: forecasting model comparison ─────────────────────────────────────

def part_a(d, model):
    log("Part A: forecasting model comparison")
    Xtr, ytr, Xte, yte = d["X_train"], d["y_train"], d["X_test"], d["y_test"]
    results = {}

    # Seasonal naive: the real reading at the same 15-min slot 7 days earlier
    raw_series = d["raw"].set_index("Timestamp")[TARGET]
    lookup = lambda ts: raw_series.reindex(ts - pd.Timedelta("7D")).values
    lag = lookup(d["ts_test"])
    ok = ~np.isnan(lag)
    results["Seasonal naive (same slot, 7 days earlier)"] = {
        **metrics(yte.values[ok], lag[ok]),
        "coverage": float(ok.mean()), "train_seconds": 0.0, "tuning_seconds": 0.0,
        "inference_ms_per_1000": inference_ms_per_1000(lambda _: lookup(d["ts_test"]), d["ts_test"]),
    }

    # Linear Regression
    t0 = time.perf_counter()
    lr = LinearRegression().fit(Xtr, ytr)
    lr_train = time.perf_counter() - t0
    results["Linear Regression"] = {
        **metrics(yte, lr.predict(Xte)), "train_seconds": lr_train, "tuning_seconds": 0.0,
        "inference_ms_per_1000": inference_ms_per_1000(lr.predict, Xte),
        "coefficients": dict(zip(FEATURES, lr.coef_)), "intercept": float(lr.intercept_),
    }

    # Random Forest, Optuna with the same budget/split/subsample as XGBoost in notebook 1
    val_idx = int(len(Xtr) * 0.80)
    X_tr, y_tr, X_val, y_val = Xtr.iloc[:val_idx], ytr.iloc[:val_idx], Xtr.iloc[val_idx:], ytr.iloc[val_idx:]
    rng = np.random.RandomState(SEED)
    sample_idx = rng.choice(len(X_tr), size=min(10000, len(X_tr)), replace=False)
    X_opt, y_opt = X_tr.iloc[sample_idx], y_tr.iloc[sample_idx]

    def rf_objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "max_depth": trial.suggest_int("max_depth", 4, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
            "max_features": trial.suggest_categorical("max_features", [1.0, 0.7, 0.5, "sqrt"]),
        }
        m = RandomForestRegressor(**params, n_jobs=-1, random_state=SEED).fit(X_opt, y_opt)
        return float(np.sqrt(mean_squared_error(y_val, m.predict(X_val))))

    t0 = time.perf_counter()
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(rf_objective, n_trials=50)
    rf_tuning = time.perf_counter() - t0
    rf_params = study.best_params
    log(f"  RF Optuna done in {rf_tuning:.0f}s, best val RMSE {study.best_value:.4f}: {rf_params}")
    t0 = time.perf_counter()
    rf = RandomForestRegressor(**rf_params, n_jobs=-1, random_state=SEED).fit(Xtr, ytr)
    rf_train = time.perf_counter() - t0
    results["Random Forest (Optuna-tuned)"] = {
        **metrics(yte, rf.predict(Xte)), "train_seconds": rf_train, "tuning_seconds": rf_tuning,
        "inference_ms_per_1000": inference_ms_per_1000(rf.predict, Xte),
        "best_params": rf_params, "best_val_rmse": float(study.best_value), "optuna_trials": 50,
    }

    # Deployed XGBoost: metrics from the saved model. Training time is measured
    # on a throw-away refit with identical params; the deployed file is untouched.
    xgb_params = {k: model.get_params()[k] for k in [
        "n_estimators", "max_depth", "learning_rate", "subsample", "colsample_bytree",
        "min_child_weight", "reg_alpha", "reg_lambda", "random_state"]}
    t0 = time.perf_counter()
    xgb.XGBRegressor(**xgb_params).fit(Xtr, ytr)
    xgb_train = time.perf_counter() - t0
    results["XGBoost (deployed, Optuna-tuned)"] = {
        **metrics(yte, model.predict(Xte)), "train_seconds": xgb_train,
        "train_seconds_note": "timed on a throw-away refit with identical params; metrics are from the deployed xgb_model.pkl",
        "tuning_seconds": None, "inference_ms_per_1000": inference_ms_per_1000(model.predict, Xte),
        "params": xgb_params, "optuna_trials": 50,
    }

    # 5-fold rolling-origin CV over the whole cleaned series
    log("  rolling-origin CV (5 folds)")
    tss = TimeSeriesSplit(n_splits=5)
    makers = {
        "Linear Regression": lambda: LinearRegression(),
        "Random Forest (Optuna-tuned)": lambda: RandomForestRegressor(**rf_params, n_jobs=-1, random_state=SEED),
        "XGBoost (deployed params)": lambda: xgb.XGBRegressor(**xgb_params),
    }
    cv = {name: [] for name in makers}
    folds = []
    X, y, ts = d["X"], d["y"], d["clean"]["Timestamp"]
    for k, (tr_i, te_i) in enumerate(tss.split(X)):
        folds.append({"fold": k + 1, "train_rows": len(tr_i), "test_rows": len(te_i),
                      "test_start": str(ts.iloc[te_i[0]]), "test_end": str(ts.iloc[te_i[-1]])})
        for name, make in makers.items():
            m = make().fit(X.iloc[tr_i], y.iloc[tr_i])
            cv[name].append(metrics(y.iloc[te_i], m.predict(X.iloc[te_i])))
        log(f"    fold {k + 1} done")
    cv_summary = {
        name: {m: {"mean": float(np.mean([f[m] for f in fs])), "std": float(np.std([f[m] for f in fs]))}
               for m in ["rmse", "mae", "mape", "r2"]} | {"folds": fs}
        for name, fs in cv.items()
    }

    # Figures: RMSE and MAPE, log scale (values span 1e-8 to ~270)
    order = list(results.keys())
    short = {"Seasonal naive (same slot, 7 days earlier)": "Seasonal naive",
             "Linear Regression": "Linear Regression",
             "Random Forest (Optuna-tuned)": "Random Forest (tuned)",
             "XGBoost (deployed, Optuna-tuned)": "XGBoost (deployed)"}
    fig, axes = new_fig(11, 3.6, 1, 2)
    for ax, key, label, unit in [(axes[0], "rmse", "Test RMSE", "kW"), (axes[1], "mape", "Test MAPE", "%")]:
        vals = [max(results[n][key], 1e-12) for n in order]
        colors = [C_SHAP if n.startswith("XGBoost") else TEXT_2 for n in order]
        ax.barh([short[n] for n in order], vals, color=colors, height=0.55)
        ax.set_xscale("log")
        ax.invert_yaxis()
        ax.set_title(f"{label} ({unit}, log scale)", fontsize=11, loc="left")
        for i, v in enumerate(vals):
            txt = f"{v:.2e}" if v < 0.01 else f"{v:.3f}" if v < 10 else f"{v:.1f}"
            ax.text(v * 1.4, i, txt, va="center", color=TEXT, fontsize=9)
        ax.set_xlim(min(vals) / 5, max(vals) * 2000)
        ax.grid(axis="y", visible=False)
    fig.suptitle("Forecasting models on the chronological test set (37,722 rows)", color=TEXT, x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.subplots_adjust(wspace=0.45)
    figs = [save_fig(fig, "model_comparison_rmse_mape.png")]

    out = {
        "description": "Same IQR cleaning and chronological 80/20 split as notebook 1; test rows 2024-05-01 08:00 to 2025-05-31 23:45.",
        "split": {"train_rows": len(Xtr), "test_rows": len(Xte),
                  "test_start": str(d["ts_test"].iloc[0]), "test_end": str(d["ts_test"].iloc[-1])},
        "holdout": results,
        "cross_validation": {"method": "sklearn TimeSeriesSplit(n_splits=5), expanding window over all 188,607 cleaned rows",
                             "folds": folds, "results": cv_summary},
        "figures": figs,
    }
    save_json(out, "model_comparison_v2.json")
    return out


# ── Part B: SHAP vs LIME ─────────────────────────────────────────────────────

def demand_thresholds(clean):
    return (clean[TARGET].quantile(0.25), clean[TARGET].quantile(0.75), clean[TARGET].quantile(0.90))


def level_of(v, th):
    p25, p75, p90 = th
    return "low" if v < p25 else "medium" if v < p75 else "high" if v < p90 else "peak"


def make_lime(clean):
    """Identical to backend/app.py load_live_explainer()."""
    bg = clean.sample(2000, random_state=SEED)[FEATURE_COLS].copy()
    bg.columns = FEATURES
    return LimeTabularExplainer(training_data=bg.values, feature_names=FEATURES,
                                mode="regression", random_state=SEED, verbose=False)


def lime_explain(explainer, model, x, seed):
    predict = lambda X: model.predict(pd.DataFrame(X, columns=FEATURES))
    explainer.random_state.seed(seed)   # shared by explainer, LimeBase and discretizer
    t0 = time.perf_counter()
    exp = explainer.explain_instance(x, predict, num_features=len(FEATURES), num_samples=1000)
    secs = time.perf_counter() - t0
    w = np.zeros(len(FEATURES))
    for fi, wt in exp.local_exp[1]:   # key 1 holds the real weights in regression mode
        w[fi] = wt
    rules = {fi: rule for (fi, _), (rule, _) in zip(exp.local_exp[1], exp.as_list(label=1))}
    intercept = exp.intercept[1] if isinstance(exp.intercept, dict) else exp.intercept
    return {"weights": w, "rules": [rules[i] for i in range(len(FEATURES))], "r2": float(exp.score),
            "local_pred": float(exp.local_pred[0]), "intercept": float(intercept), "seconds": secs}


def part_b(d, model):
    log("Part B: SHAP vs LIME")
    clean, Xtr, Xte, yte = d["clean"], d["X_train"], d["X_test"], d["y_test"]
    th = demand_thresholds(clean)
    test = Xte.copy()
    test["_y"] = yte.values
    test["_level"] = [level_of(v, th) for v in yte.values]
    # 200 test instances, 50 per demand level
    inst = pd.concat([test[test["_level"] == lv].sample(50, random_state=SEED) for lv in LEVELS])
    Xi = inst[FEATURES]
    pred_i = model.predict(Xi)

    tree = shap.TreeExplainer(model)
    base = float(np.ravel(tree.expected_value)[0])
    t_mean_train = float(Xtr["Temperature"].mean())

    # Global SHAP on a 2,000-row test sample
    Xs = Xte.sample(2000, random_state=SEED)
    t0 = time.perf_counter()
    phi_s = tree.shap_values(Xs)
    shap_batch_s = (time.perf_counter() - t0) / len(Xs)
    pred_s = model.predict(Xs)
    true_t = 100.0 * (Xs["Temperature"].values - t_mean_train)
    slope, icpt = np.polyfit(true_t, phi_s[:, 0], 1)
    additivity = np.abs(base + phi_s.sum(1) - pred_s)
    abs_share = np.abs(phi_s).sum(0) / np.abs(phi_s).sum()

    # Single-instance SHAP timing
    t0 = time.perf_counter()
    for k in range(50):
        tree.shap_values(Xi.iloc[[k]])
    shap_single_s = (time.perf_counter() - t0) / 50

    # SHAP + LIME on the 200 instances
    phi_i = tree.shap_values(Xi)
    lime_exp = make_lime(clean)
    lime_runs = [lime_explain(lime_exp, model, Xi.iloc[k].values.astype(float), SEED) for k in range(len(Xi))]
    W = np.array([r["weights"] for r in lime_runs])
    lime_r2 = np.array([r["r2"] for r in lime_runs])
    lime_gap = np.abs(np.array([r["local_pred"] for r in lime_runs]) - pred_i)
    lime_rank1 = np.argmax(np.abs(W), 1) == 0
    lime_t_share = np.abs(W[:, 0]) / np.abs(W).sum(1)
    shap_rank1 = np.argmax(np.abs(phi_i), 1) == 0
    # Sign check: does each method push the prediction the right way for Temperature?
    true_sign = np.sign(Xi["Temperature"].values - t_mean_train)
    shap_sign_ok = np.sign(phi_i[:, 0]) == true_sign
    lime_sign_ok = np.sign(W[:, 0]) == true_sign

    by_level = {}
    for lv in LEVELS:
        m = (inst["_level"] == lv).values
        by_level[lv] = {
            "n": int(m.sum()),
            "lime_r2_mean": float(lime_r2[m].mean()), "lime_r2_min": float(lime_r2[m].min()), "lime_r2_max": float(lime_r2[m].max()),
            "lime_abs_localpred_minus_pred_mean_kw": float(lime_gap[m].mean()),
            "lime_abs_localpred_minus_pred_max_kw": float(lime_gap[m].max()),
            "lime_temperature_rank1_pct": float(lime_rank1[m].mean() * 100),
            "shap_temperature_rank1_pct": float(shap_rank1[m].mean() * 100),
        }

    # Agreement per instance: Spearman of |attribution| and top-3 overlap
    sp_all, sp_rest, top3, top1 = [], [], [], []
    for k in range(len(Xi)):
        a, b = np.abs(phi_i[k]), np.abs(W[k])
        sp_all.append(spearmanr(a, b).correlation)
        sp_rest.append(spearmanr(a[1:], b[1:]).correlation)
        top3.append(len(set(np.argsort(-a)[:3]) & set(np.argsort(-b)[:3])) / 3)
        top1.append(np.argmax(a) == np.argmax(b))

    # LIME stability: 30 instances (7/8/7/8) x 10 seeds
    log("  LIME stability: 30 instances x 10 seeds")
    pick = {"low": 7, "medium": 8, "high": 7, "peak": 8}
    stab_idx = np.concatenate([np.where(inst["_level"].values == lv)[0][:n] for lv, n in pick.items()])
    seeds = list(range(10))
    stab = []
    for k in stab_idx:
        runs = [lime_explain(lime_exp, model, Xi.iloc[k].values.astype(float), s) for s in seeds]
        Wk = np.array([r["weights"] for r in runs])
        top1s = [int(np.argmax(np.abs(w))) for w in Wk]
        top3s = [set(np.argsort(-np.abs(w))[:3]) for w in Wk]
        modal = max(set(top1s), key=top1s.count)
        jac = [len(top3s[i] & top3s[j]) / len(top3s[i] | top3s[j]) for i in range(10) for j in range(i + 1, 10)]
        stab.append({
            "instance": int(k), "level": inst["_level"].values[k], "temperature": float(Xi.iloc[k]["Temperature"]),
            "temperature_weights": Wk[:, 0].tolist(),
            "temperature_weight_mean": float(Wk[:, 0].mean()), "temperature_weight_std": float(Wk[:, 0].std()),
            "r2_values": [r["r2"] for r in runs],
            "top1_agreement": top1s.count(modal) / len(top1s), "top1_modal_feature": FEATURES[modal],
            "top3_mean_pairwise_jaccard": float(np.mean(jac)),
        })

    # SHAP stability (a): global importance on 5 different 2,000-row samples
    log("  SHAP stability: 5 sample seeds + 5 background seeds")
    glob = []
    for s in range(5):
        ph = tree.shap_values(Xte.sample(2000, random_state=s))
        glob.append(np.abs(ph).mean(0))
    glob = np.array(glob)
    # SHAP stability (b): interventional SHAP with 5 different 100-row backgrounds,
    # fixed 300 instances. shap 0.52's interventional TreeExplainer rejects this
    # XGBoost 3.x model ("categorical split not supported"), so the model-agnostic
    # PermutationExplainer with an Independent masker is used for this test.
    Xfix = Xte.sample(300, random_state=SEED)
    f_np = lambda X: model.predict(pd.DataFrame(X, columns=FEATURES))
    inter = []
    for s in range(5):
        bg = Xtr.sample(100, random_state=s).values
        pe = shap.explainers.Permutation(f_np, shap.maskers.Independent(bg, max_samples=100), seed=s)
        inter.append(pe(Xfix.values, max_evals=2 * len(FEATURES) + 1, silent=True).values)
    inter = np.array(inter)                       # (5 seeds, 300, 12)
    inter_t_std = inter[:, :, 0].std(0)
    # Interventional SHAP is relative to the background's mean, so a new
    # background shifts every Temperature value by the same constant
    # (100 x difference in background mean T). Removing that per-seed offset
    # leaves the instance-level instability.
    seed_offset = inter[:, :, 0].mean(1)
    inter_t_std_centered = (inter[:, :, 0] - seed_offset[:, None]).std(0)
    bg_mean_t = np.array([Xtr.sample(100, random_state=s)["Temperature"].mean() for s in range(5)])
    inter_top1 = (np.argmax(np.abs(inter), 2) == 0).mean()

    stab_t_std = np.array([s["temperature_weight_std"] for s in stab])
    summary = {
        "ground_truth": {
            "statement": "Load = 100 * Temperature - 1300 exactly (max residual 5e-7 kW); the other 11 features have zero effect.",
            "true_temperature_contribution": "100 * (T - mean T of training data)",
            "train_mean_temperature": t_mean_train,
            "shap_pct_attribution_on_temperature": float(abs_share[0] * 100),
            "shap_temperature_vs_truth_pearson_r": float(np.corrcoef(true_t, phi_s[:, 0])[0, 1]),
            "shap_temperature_vs_truth_slope": float(slope), "shap_temperature_vs_truth_intercept_kw": float(icpt),
            "shap_temperature_vs_truth_rmse_kw": float(np.sqrt(np.mean((phi_s[:, 0] - true_t) ** 2))),
            "shap_temperature_rank1_pct": float(shap_rank1.mean() * 100),
            "shap_temperature_sign_correct_pct": float(shap_sign_ok.mean() * 100),
            "lime_mean_pct_attribution_on_temperature": float(lime_t_share.mean() * 100),
            "lime_temperature_rank1_pct": float(lime_rank1.mean() * 100),
            "lime_temperature_rank1_every_instance": bool(lime_rank1.all()),
            "lime_temperature_sign_correct_pct": float(lime_sign_ok.mean() * 100),
            "n_instances_lime": len(Xi), "n_instances_shap_global": len(Xs),
        },
        "fidelity": {
            "shap_base_value_kw": base,
            "shap_additivity_abs_error_mean_kw": float(additivity.mean()),
            "shap_additivity_abs_error_max_kw": float(additivity.max()),
            "lime_r2_mean": float(lime_r2.mean()), "lime_r2_min": float(lime_r2.min()), "lime_r2_max": float(lime_r2.max()),
            "lime_abs_localpred_minus_pred_mean_kw": float(lime_gap.mean()),
            "lime_abs_localpred_minus_pred_max_kw": float(lime_gap.max()),
            "by_level": by_level,
        },
        "stability": {
            "lime": {
                "n_instances": len(stab), "seeds": seeds,
                "temperature_weight_std_mean_kw": float(stab_t_std.mean()),
                "temperature_weight_std_max_kw": float(stab_t_std.max()),
                "top1_agreement_mean": float(np.mean([s["top1_agreement"] for s in stab])),
                "top3_jaccard_mean": float(np.mean([s["top3_mean_pairwise_jaccard"] for s in stab])),
                "r2_std_mean": float(np.mean([np.std(s["r2_values"]) for s in stab])),
                "by_level": {lv: {
                    "temperature_weight_std_mean_kw": float(np.mean([s["temperature_weight_std"] for s in stab if s["level"] == lv])),
                    "top3_jaccard_mean": float(np.mean([s["top3_mean_pairwise_jaccard"] for s in stab if s["level"] == lv])),
                } for lv in LEVELS},
                "instances": stab,
            },
            "shap": {
                "global_mean_abs_by_sample_seed": {"seeds": list(range(5)), "temperature_mean_kw": float(glob[:, 0].mean()),
                                                   "temperature_std_kw": float(glob[:, 0].std()),
                                                   "per_feature_mean_kw": dict(zip(FEATURES, glob.mean(0))),
                                                   "per_feature_std_kw": dict(zip(FEATURES, glob.std(0)))},
                "interventional_by_background_seed": {"seeds": list(range(5)), "background_rows": 100, "instances": 300,
                                                      "estimator": "shap PermutationExplainer + Independent masker (interventional); "
                                                                   "TreeExplainer interventional mode does not support this XGBoost 3.x model",
                                                      "temperature_value_std_mean_kw": float(inter_t_std.mean()),
                                                      "temperature_value_std_max_kw": float(inter_t_std.max()),
                                                      "baseline_offset_std_kw": float(seed_offset.std()),
                                                      "background_mean_temperature_by_seed": bg_mean_t.tolist(),
                                                      "expected_offset_std_kw_100x_bg_mean_t_std": float(100 * bg_mean_t.std()),
                                                      "temperature_value_std_after_removing_offset_mean_kw": float(inter_t_std_centered.mean()),
                                                      "temperature_value_std_after_removing_offset_max_kw": float(inter_t_std_centered.max()),
                                                      "note": "Almost all of the raw std is a uniform shift caused by each background's mean temperature; rankings and slopes do not change.",
                                                      "temperature_rank1_pct": float(inter_top1 * 100)},
                "tree_path_dependent_note": "TreeExplainer (tree_path_dependent) is deterministic: the same instance always gets identical values.",
            },
        },
        "agreement": {
            "spearman_abs_attribution_all12_mean": float(np.nanmean(sp_all)),
            "spearman_abs_attribution_excluding_temperature_mean": float(np.nanmean(sp_rest)),
            "top1_same_feature_pct": float(np.mean(top1) * 100),
            "top3_overlap_mean": float(np.mean(top3)),
            "note": "Both methods put Temperature first. Ranks 2-12 are features with zero true effect, so their order is noise in both methods and low agreement there is expected.",
        },
        "runtime": {
            "shap_seconds_per_explanation_batch": shap_batch_s,
            "shap_seconds_per_explanation_single": shap_single_s,
            "lime_seconds_per_explanation_mean": float(np.mean([r["seconds"] for r in lime_runs])),
            "lime_num_samples": 1000,
        },
    }

    figs = []
    # 1. SHAP beeswarm
    shap.summary_plot(phi_s, Xs, show=False, max_display=12, color_bar=True, plot_size=(8, 5.5))
    fig = plt.gcf()
    fig.set_facecolor(SURFACE)
    for ax in fig.axes:
        ax.set_facecolor(SURFACE)
        ax.tick_params(colors=TEXT_2)
        ax.xaxis.label.set_color(TEXT_2)
        ax.yaxis.label.set_color(TEXT_2)
        for s in ax.spines.values():
            s.set_color(GRID)
        for t in ax.get_yticklabels():
            t.set_color(TEXT)
    fig.axes[0].set_title("SHAP beeswarm, deployed XGBoost (2,000 test rows)", color=TEXT, loc="left", fontsize=11)
    figs.append(save_fig(fig, "shap_beeswarm.png"))

    # 2. SHAP bar (mean |SHAP|), linear scale so dominance is visible as it is
    mean_abs = np.abs(phi_s).mean(0)
    order = np.argsort(mean_abs)
    fig, ax = new_fig(8, 4.8)
    ax.barh([FEATURES[i] for i in order], mean_abs[order], color=C_SHAP, height=0.6)
    for j, i in enumerate(order):
        ax.text(mean_abs[i] + 2, j, f"{mean_abs[i]:.3f} kW", va="center", color=TEXT, fontsize=8.5)
    ax.set_xlim(0, mean_abs.max() * 1.25)
    ax.set_xlabel("mean |SHAP| (kW)")
    ax.set_title("Global importance: mean |SHAP| per feature", loc="left", fontsize=11)
    ax.grid(axis="y", visible=False)
    figs.append(save_fig(fig, "shap_bar.png"))

    # 3. SHAP dependence for Temperature vs the true line
    fig, ax = new_fig(8, 4.8)
    T = Xs["Temperature"].values
    ax.scatter(T, phi_s[:, 0], s=9, color=C_SHAP, alpha=0.55, linewidths=0, label="SHAP value (deployed model)")
    tt = np.linspace(T.min(), T.max(), 50)
    ax.plot(tt, 100 * (tt - t_mean_train), color=C_LIME, linewidth=2, label="true effect 100 × (T − mean T)")
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("SHAP value for Temperature (kW)")
    ax.set_title(f"SHAP recovers the true effect: r = {summary['ground_truth']['shap_temperature_vs_truth_pearson_r']:.5f}, "
                 f"slope = {slope:.3f}", loc="left", fontsize=11)
    leg = ax.legend(facecolor=SURFACE, edgecolor=GRID, fontsize=9, loc="upper left")
    for t in leg.get_texts():
        t.set_color(TEXT)
    figs.append(save_fig(fig, "shap_dependence_temperature.png"))

    # 4/5. LIME examples: highest-demand peak instance and lowest-demand low instance
    for lv, pick_fn, fname in [("peak", np.argmax, "lime_example_peak.png"), ("low", np.argmin, "lime_example_low.png")]:
        idx_lv = np.where(inst["_level"].values == lv)[0]
        k = idx_lv[pick_fn(inst["_y"].values[idx_lv])]
        r = lime_runs[k]
        o = np.argsort(np.abs(r["weights"]))
        fig, ax = new_fig(8.5, 4.8)
        ax.barh([r["rules"][i] for i in o], r["weights"][o],
                color=[C_POS if r["weights"][i] >= 0 else C_NEG for i in o], height=0.6)
        ax.axvline(0, color=TEXT_2, linewidth=0.8)
        ax.set_xlabel("LIME weight (kW)")
        ax.set_title(f"LIME, {lv} instance: actual {inst['_y'].values[k]:.0f} kW, XGBoost {pred_i[k]:.0f} kW, "
                     f"LIME local {r['local_pred']:.0f} kW, R² {r['r2']:.2f}", loc="left", fontsize=10)
        ax.grid(axis="y", visible=False)
        lim = np.abs(r["weights"]).max() * 1.15
        ax.set_xlim(-lim, lim)
        figs.append(save_fig(fig, fname))

    # 6. LIME stability box plot: Temperature weight over 10 seeds, per instance
    fig, ax = new_fig(11, 4.4)
    data = [s["temperature_weights"] for s in stab]
    bp = ax.boxplot(data, patch_artist=True, widths=0.6, medianprops={"color": TEXT, "linewidth": 1.4},
                    whiskerprops={"color": TEXT_2}, capprops={"color": TEXT_2},
                    flierprops={"markerfacecolor": C_LIME, "markeredgecolor": C_LIME, "markersize": 4})
    for patch in bp["boxes"]:
        patch.set_facecolor(C_LIME)
        patch.set_alpha(0.7)
        patch.set_edgecolor(C_LIME)
    ax.set_xticks(range(1, len(stab) + 1))
    ax.set_xticklabels([f"{s['level'][0].upper()}{i + 1}" for i, s in enumerate(stab)], fontsize=8)
    ax.axhline(0, color=TEXT_2, linewidth=0.8)
    ax.set_ylabel("LIME Temperature weight (kW)")
    ax.set_title(f"LIME stability: Temperature weight across 10 seeds for 30 instances "
                 f"(mean std {stab_t_std.mean():.1f} kW). L/M/H/P = demand level", loc="left", fontsize=10)
    figs.append(save_fig(fig, "lime_stability_box.png"))

    # 7. SHAP vs LIME comparison table image
    g, f, st, ag, rt = summary["ground_truth"], summary["fidelity"], summary["stability"], summary["agreement"], summary["runtime"]
    rows = [
        ["Share of attribution on Temperature", f"{g['shap_pct_attribution_on_temperature']:.2f}%", f"{g['lime_mean_pct_attribution_on_temperature']:.1f}%"],
        ["Temperature ranked #1", f"{g['shap_temperature_rank1_pct']:.0f}% of rows", f"{g['lime_temperature_rank1_pct']:.0f}% of instances"],
        ["Temperature sign correct", f"{g['shap_temperature_sign_correct_pct']:.1f}%", f"{g['lime_temperature_sign_correct_pct']:.1f}%"],
        ["Match to true effect 100·(T − mean T)", f"r = {g['shap_temperature_vs_truth_pearson_r']:.5f}", "n/a (weights are per quartile bin)"],
        ["Fidelity", f"additivity error max {f['shap_additivity_abs_error_max_kw']:.1e} kW", f"local R² mean {f['lime_r2_mean']:.2f} (min {f['lime_r2_min']:.2f})"],
        ["|explanation total − model prediction|", f"max {f['shap_additivity_abs_error_max_kw']:.3f} kW (additive)", f"mean {f['lime_abs_localpred_minus_pred_mean_kw']:.0f} kW"],
        ["Stability across seeds", f"deterministic; ±{st['shap']['interventional_by_background_seed']['temperature_value_std_after_removing_offset_mean_kw']:.3f} kW (5 bkgds)",
         f"T weight std {st['lime']['temperature_weight_std_mean_kw']:.1f} kW; top-3 Jaccard {st['lime']['top3_jaccard_mean']:.2f}"],
        ["Runtime per explanation", f"{rt['shap_seconds_per_explanation_single'] * 1000:.1f} ms", f"{rt['lime_seconds_per_explanation_mean'] * 1000:.0f} ms"],
        ["Agreement SHAP vs LIME", f"top-1 same {ag['top1_same_feature_pct']:.0f}%", f"top-3 overlap {ag['top3_overlap_mean']:.2f}"],
    ]
    fig, ax = plt.subplots(figsize=(11, 4.2), facecolor=SURFACE)
    ax.axis("off")
    tbl = ax.table(cellText=rows, colLabels=["Criterion", "SHAP TreeExplainer", "LIME (1,000 samples)"],
                   loc="center", cellLoc="left", colLoc="left", colWidths=[0.34, 0.33, 0.33])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.6)
    for (r_, c_), cell in tbl.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_facecolor("#101F30" if r_ == 0 else SURFACE)
        cell.get_text().set_color(TEXT if r_ == 0 or c_ == 0 else TEXT_2)
        if r_ == 0:
            cell.get_text().set_fontweight("bold")
    ax.set_title("SHAP vs LIME on the deployed XGBoost, scored against the known ground truth",
                 color=TEXT, loc="left", fontsize=11)
    figs.append(save_fig(fig, "shap_vs_lime_table.png"))

    summary["table_rows"] = rows
    summary["figures"] = figs
    summary["setup"] = {
        "instances": "200 test-set rows, 50 per demand level (p25/p75/p90 of cleaned data), random_state=42",
        "lime": "LimeTabularExplainer as in backend/app.py: 2,000-row background, quartile discretizer, num_samples=1000, re-seeded per explanation",
        "shap": "shap.TreeExplainer(model) (tree_path_dependent) unless stated",
    }
    save_json(summary, "xai_comparison.json")
    return summary


# ── Part C: temporal drift with bootstrap CIs ────────────────────────────────

def part_c(d, model, n_boot=20):
    log("Part C: temporal drift with the deployed model + bootstrap CIs")
    clean = d["clean"]
    years = sorted(clean["Timestamp"].dt.year.unique())
    tree = shap.TreeExplainer(model)
    rng = np.random.RandomState(SEED)
    per_year = {}
    for yr in years:
        rows = clean[clean["Timestamp"].dt.year == yr]
        Xy = rows[FEATURE_COLS].copy()
        Xy.columns = FEATURES
        phi = np.abs(tree.shap_values(Xy))
        boots = np.array([phi[rng.randint(0, len(phi), len(phi))].mean(0) for _ in range(n_boot)])
        per_year[str(yr)] = {
            "rows": len(Xy),
            "mean_abs_shap": dict(zip(FEATURES, phi.mean(0))),
            "ci_low": dict(zip(FEATURES, np.percentile(boots, 2.5, axis=0))),
            "ci_high": dict(zip(FEATURES, np.percentile(boots, 97.5, axis=0))),
            "temperature_mean_c": float(Xy["Temperature"].mean()),
            "temperature_mean_abs_dev_c": float(np.abs(Xy["Temperature"] - Xy["Temperature"].mean()).mean()),
        }
        log(f"  {yr}: {len(Xy)} rows")

    def overlap(a, b, f):
        return not (per_year[a]["ci_high"][f] < per_year[b]["ci_low"][f] or per_year[b]["ci_high"][f] < per_year[a]["ci_low"][f])

    ys = [str(y) for y in years]
    first, last = ys[0], ys[-1]
    drift = {}
    for f in FEATURES:
        adjacent = [{"from": a, "to": b, "change_kw": per_year[b]["mean_abs_shap"][f] - per_year[a]["mean_abs_shap"][f],
                     "cis_overlap": overlap(a, b, f)} for a, b in zip(ys, ys[1:])]
        drift[f] = {
            "change_first_to_last_kw": per_year[last]["mean_abs_shap"][f] - per_year[first]["mean_abs_shap"][f],
            "first_to_last_cis_overlap": overlap(first, last, f),
            "flagged_first_to_last": not overlap(first, last, f),
            "adjacent_years": adjacent,
            "flagged_adjacent_pairs": [f"{p['from']}->{p['to']}" for p in adjacent if not p["cis_overlap"]],
        }
    v1 = json.load(open(COMPONENT / "backend" / "outputs" / "temporal_drift.json", encoding="utf-8"))

    # Figure: small multiples, one panel per feature, each with its own y scale
    fig, axes = new_fig(13, 8.5, 3, 4, sharex=True)
    xs = [int(y) for y in ys]
    for ax, f in zip(axes.ravel(), FEATURES):
        m = [per_year[y]["mean_abs_shap"][f] for y in ys]
        lo = [per_year[y]["ci_low"][f] for y in ys]
        hi = [per_year[y]["ci_high"][f] for y in ys]
        ax.fill_between(xs, lo, hi, color=C_SHAP, alpha=0.25, linewidth=0)
        ax.plot(xs, m, color=C_SHAP, linewidth=2, marker="o", markersize=4)
        flag = " (drift)" if drift[f]["flagged_first_to_last"] else ""
        ax.set_title(f + flag, loc="left", fontsize=10)
        ax.tick_params(labelsize=8)
    for ax in axes[-1]:
        ax.set_xticks(xs)
    fig.suptitle(f"Mean |SHAP| per year (kW), deployed model, {n_boot} bootstrap resamples, shaded = 95% CI. "
                 f"Each panel has its own scale.", color=TEXT, x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    figs = [save_fig(fig, "temporal_drift_v2.png")]

    out = {
        "method": "One deployed model (xgb_model.pkl). SHAP TreeExplainer on every cleaned row of each year; "
                  f"{n_boot} bootstrap resamples of those rows give the 95% percentile CI. Drift is flagged only "
                  "when the 95% CIs of two years do not overlap. Because the model is fixed, any change reflects "
                  "a change in that year's input data, not a change in the model.",
        "years": ys, "features": FEATURES, "n_bootstrap": n_boot, "per_year": per_year, "drift": drift,
        "flagged_first_to_last": [f for f in FEATURES if drift[f]["flagged_first_to_last"]],
        "v1_comparison": {
            "v1_method": "notebook 1: a separate XGBoost refit per year on 2,000 rows, SHAP on the same rows, no CI",
            "v1_biggest_gainer": v1["insights"]["biggest_gainer"], "v1_biggest_loser": v1["insights"]["biggest_loser"],
            "v1_gainer_flagged_in_v2": drift[v1["insights"]["biggest_gainer"]["feature"]]["flagged_first_to_last"],
            "v1_loser_flagged_in_v2": drift[v1["insights"]["biggest_loser"]["feature"]]["flagged_first_to_last"],
        },
        "figures": figs,
    }
    save_json(out, "temporal_drift_v2.json")
    return out


# ── Part D: cross-dataset check ──────────────────────────────────────────────

def part_d():
    log("Part D: cross-dataset check (experiments/dataset_check.py)")
    runpy.run_path(str(HERE / "dataset_check.py"), run_name="__main__")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default="A,B,C,D", help="comma-separated subset of A,B,C,D")
    args = ap.parse_args()
    parts = {p.strip().upper() for p in args.parts.split(",")}
    t0 = time.perf_counter()
    np.random.seed(SEED)
    d = load_data()
    model = joblib.load(MODEL_PATH)
    log(f"data: {len(d['raw'])} rows, {len(d['clean'])} after IQR, train {len(d['X_train'])}, test {len(d['X_test'])}")
    timings = {}
    for p, fn in [("A", lambda: part_a(d, model)), ("B", lambda: part_b(d, model)),
                  ("C", lambda: part_c(d, model)), ("D", part_d)]:
        if p in parts:
            s = time.perf_counter()
            fn()
            timings[p] = round(time.perf_counter() - s, 1)
            log(f"part {p} took {timings[p]} s")
    log(f"total {time.perf_counter() - t0:.0f} s; per part {timings}")


if __name__ == "__main__":
    main()
