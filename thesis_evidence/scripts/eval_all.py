"""Evidence-gathering evaluation for the Behaviour Intelligence component (IT22545176).

Re-runs the component's own pipeline and comparison modules inside a scratch
workspace (so behaviour-intelligence/data and behaviour-intelligence/models are
never modified), then writes tables to thesis_evidence/tables, figures to
thesis_evidence/figures and a machine-readable summary to
thesis_evidence/tables/eval_summary.json.

Usage (from the repo root, with an interpreter that has scikit-learn):
    set PYTHONPATH=behaviour-intelligence\\backend
    python thesis_evidence\\scripts\\eval_all.py <scratch_workspace_dir>
"""
import json
import shutil
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
BI = ROOT / "behaviour-intelligence"
OUT = ROOT / "thesis_evidence"
TAB = OUT / "tables"
FIG = OUT / "figures"
WS = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(BI / "backend"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import psutil
import sklearn
from scipy import stats
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from app.ml import anomaly_comparison as ac
from app.ml import preprocessing as pp
from app.ml.anomaly_detection import run_anomaly_detection_pipeline
from app.ml.behavior_labeling import generate_behavior_labels_from_csv
from app.ml.behavior_prediction import predict_future_behavior
from app.ml.clustering import _compute_knee_eps, run_clustering_pipeline
from app.ml.daily_profile import to_daily_profiles
from app.ml.data_loader import load_raw_dataset
from app.ml.model_comparison import run_clustering_model_comparison
from app.ml.peak_detection import detect_peak_days

S = {"env": {"python": sys.version.split()[0], "sklearn": sklearn.__version__,
             "pandas": pd.__version__, "numpy": np.__version__,
             "matplotlib": matplotlib.__version__}}
PROC = psutil.Process()
PCOLS = [f"p{i:02d}" for i in range(96)]
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LABELS = ["Normal Weekday Demand", "Peak Demand Day", "Holiday / Low Demand Day", "Abnormal Demand Day"]

# ── chart style (light surface, fixed categorical order) ────────────────────
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
LABEL_COLOR = dict(zip(LABELS, C[:4]))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.family": "DejaVu Sans", "font.size": 9.5, "text.color": INK,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "legend.frameon": False, "lines.linewidth": 2, "savefig.dpi": 200, "savefig.bbox": "tight",
})
HOURS = np.arange(96) / 4
FIGS = []


def save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)
    FIGS.append(name)
    print("figure:", name)


def hour_axis(ax):
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)])
    ax.set_xlim(0, 24)
    ax.set_xlabel("Time of day")


def timed(fn, *a, **k):
    t = time.perf_counter()
    r = fn(*a, **k)
    return r, round(time.perf_counter() - t, 3)


# ── 0. scratch workspace ────────────────────────────────────────────────────
for d in ["data/raw", "data/processed", "models"]:
    (WS / d).mkdir(parents=True, exist_ok=True)
RAW = WS / "data/raw/synthetic_realistic_load.csv"
if not RAW.exists():
    shutil.copy(BI / "data/raw/synthetic_realistic_load.csv", RAW)
PROC_DIR, MOD_DIR = WS / "data/processed", WS / "models"

# ── 1. raw data + preprocessing step counts ─────────────────────────────────
(df_raw, ts_col, dem_col), t_load = timed(load_raw_dataset, RAW)
raw_all = pd.read_csv(RAW)
S["raw"] = {
    "file": "behaviour-intelligence/data/raw/synthetic_realistic_load.csv",
    "rows": len(raw_all), "cols": raw_all.shape[1], "columns": list(raw_all.columns),
    "ts_min": str(df_raw[ts_col].min()), "ts_max": str(df_raw[ts_col].max()),
    "duplicate_timestamps": int(df_raw[ts_col].duplicated().sum()),
    "nulls": int(raw_all.isna().sum().sum()),
    "demand_describe": {k: round(float(v), 2) for k, v in df_raw[dem_col].describe().items()},
    "corr_load_temperature": round(float(raw_all.iloc[:, 1].corr(raw_all.iloc[:, 2])), 4),
    "corr_load_solar": round(float(raw_all.iloc[:, 1].corr(raw_all.iloc[:, 3])), 4),
}
steps = [("0 raw", len(df_raw), "")]
d = pp.remove_obvious_invalid_values(df_raw, dem_col)
steps.append(("1 remove NaN / negative", len(d), "dropna + demand >= 0"))
q1, q3, med = d[dem_col].quantile(.25), d[dem_col].quantile(.75), d[dem_col].median()
ub = med + 10 * (q3 - q1)
d = pp.remove_extreme_spikes(d, dem_col)
steps.append(("2 remove extreme spikes", len(d), f"demand <= median + 10*IQR = {ub:.2f} kW"))
d = pp.fill_missing_values(d, dem_col)
steps.append(("3 interpolate / ffill / bfill", len(d), "linear, both directions"))
q1, q3 = d[dem_col].quantile(.25), d[dem_col].quantile(.75)
lo, hi = q1 - 3 * (q3 - q1), q3 + 3 * (q3 - q1)
d = pp.remove_outliers_iqr(d, dem_col)
steps.append(("4 remove IQR outliers (factor 3)", len(d), f"keep [{lo:.2f}, {hi:.2f}] kW; Q1={q1:.2f}, Q3={q3:.2f}"))
d2 = pp.resample_to_15min(d, ts_col, dem_col)
steps.append(("5 resample 15min mean + interpolate", len(d2), "gaps left by step 4 are re-filled by linear interpolation"))
d3 = pp.add_helper_columns(d2)
steps.append(("6 add Date/Hour/TimeSlot", len(d3), f"columns={list(d3.columns)}"))
prof = to_daily_profiles(d3)
slots_per_day = d3.groupby("Date").size()
incomplete = slots_per_day[slots_per_day < 96]
steps.append(("7 daily 96-slot profiles", len(prof),
              f"dropped incomplete days: {[(str(k), int(v)) for k, v in incomplete.items()]}"))
pd.DataFrame(steps, columns=["step", "rows_after", "detail"]).to_csv(TAB / "T01_preprocessing_steps.csv", index=False)
S["preprocessing_steps"] = steps

# ── 2. full pipeline in scratch, stage timings + memory ─────────────────────
timing = []
rss0 = PROC.memory_info().rss
(df_clean), t = timed(pp.preprocess_timeseries, df_raw, ts_col, dem_col)
timing.append(("load_raw_dataset", t_load))
timing.append(("preprocess_timeseries", t))
df_clean.to_csv(PROC_DIR / "cleaned_data.csv", index=False)
profiles, t = timed(to_daily_profiles, df_clean)
timing.append(("to_daily_profiles", t))
profiles.to_csv(PROC_DIR / "daily_profiles.csv", index=False)
clu, t = timed(run_clustering_pipeline, PROC_DIR / "daily_profiles.csv", MOD_DIR, PROC_DIR / "clustering_results.csv")
timing.append(("run_clustering_pipeline (k=2..12 sweep + KMeans + DBSCAN)", t))
ano, t = timed(run_anomaly_detection_pipeline, PROC_DIR / "daily_profiles.csv", PROC_DIR / "clustering_results.csv",
               MOD_DIR, PROC_DIR / "anomaly_results.csv")
timing.append(("run_anomaly_detection_pipeline (IsolationForest + z-score)", t))
pk, t = timed(detect_peak_days, PROC_DIR / "daily_profiles.csv", PROC_DIR / "anomaly_results.csv",
              PROC_DIR / "peak_demand_results.csv")
timing.append(("detect_peak_days", t))
lab, t = timed(generate_behavior_labels_from_csv, PROC_DIR / "peak_demand_results.csv", PROC_DIR / "behavior_labels.csv")
timing.append(("generate_behavior_labels_from_csv", t))
timing.append(("TOTAL pipeline", round(sum(x[1] for x in timing), 3)))
mi = PROC.memory_info()
S["pipeline"] = {"clustering": clu, "anomaly": ano, "peak": pk, "labels": lab, "timing_s": timing,
                 "rss_before_mb": round(rss0 / 2**20, 1), "rss_after_mb": round(mi.rss / 2**20, 1),
                 "peak_working_set_mb": round(getattr(mi, "peak_wset", mi.rss) / 2**20, 1)}
pd.DataFrame(timing, columns=["stage", "seconds"]).to_csv(TAB / "T14_pipeline_stage_timings.csv", index=False)

# reproduction check against the saved artefacts
new = pd.read_csv(PROC_DIR / "behavior_labels.csv")
old = pd.read_csv(BI / "data/processed/behavior_labels.csv")
rep = {"same_shape": new.shape == old.shape, "same_dates": bool((new.date == old.date).all())}
for col in ["behavior_label", "behavior_risk_level", "kmeans_cluster", "dbscan_cluster",
            "final_is_anomaly", "is_peak_demand_day", "zscore_is_anomaly"]:
    rep[f"{col}_mismatches"] = int((new[col] != old[col]).sum())
for col in ["isolation_anomaly_score", "peak_demand", "mean_demand", "peak_zscore"]:
    rep[f"{col}_max_abs_diff"] = float(np.abs(new[col] - old[col]).max())
saved_metrics = json.load(open(BI / "models/clustering_metrics.json"))
rep["clustering_metrics_json_equal"] = all(
    saved_metrics[k] == json.load(open(MOD_DIR / "clustering_metrics.json"))[k] for k in saved_metrics)
S["reproduction_vs_saved"] = rep

# ── working frame ───────────────────────────────────────────────────────────
df = new.copy()
df["date"] = pd.to_datetime(df["date"])
df["dow"] = df.date.dt.dayofweek
df["month"] = df.date.dt.month
df["year"] = df.date.dt.year
df["is_weekend"] = df.dow >= 5
df["min_demand"] = df[PCOLS].min(axis=1)
df["peak_slot"] = df[PCOLS].values.argmax(axis=1)
X = df[PCOLS].values
Xs = StandardScaler().fit_transform(X)
n = len(df)
S["profiles"] = {"days": n, "date_min": str(df.date.min().date()), "date_max": str(df.date.max().date()),
                 "weekend_days": int(df.is_weekend.sum()), "weekday_days": int((~df.is_weekend).sum()),
                 "peak_demand_describe": {k: round(float(v), 2) for k, v in df.peak_demand.describe().items()},
                 "mean_demand_describe": {k: round(float(v), 2) for k, v in df.mean_demand.describe().items()},
                 "peak_skew": round(float(stats.skew(df.peak_demand)), 3),
                 "mean_skew": round(float(stats.skew(df.mean_demand)), 3)}
# structure diagnostics (same ones reports/model_comparison.md applied to the earlier dataset)
adj = [np.corrcoef(X[:, i], X[:, i + 1])[0, 1] for i in range(95)]
pca_full = PCA().fit(Xs)
S["structure_diagnostics"] = {
    "mean_adjacent_slot_correlation": round(float(np.mean(adj)), 4),
    "pca_components_for_90pct_variance": int(np.searchsorted(np.cumsum(pca_full.explained_variance_ratio_), 0.90) + 1),
    "pca_first2_explained": [round(float(v), 4) for v in pca_full.explained_variance_ratio_[:2]],
}
# same diagnostics on the earlier dataset's profiles (kept as *_OLD), for a like-for-like comparison
oldp = pd.read_csv(BI / "data/processed/daily_profiles.csv_OLD")
Xo = oldp[PCOLS].values
S["structure_diagnostics_old_dataset"] = {
    "days": len(oldp),
    "mean_adjacent_slot_correlation": round(float(np.mean([np.corrcoef(Xo[:, i], Xo[:, i + 1])[0, 1] for i in range(95)])), 4),
    "pca_components_for_90pct_variance": int(np.searchsorted(np.cumsum(PCA().fit(StandardScaler().fit_transform(Xo)).explained_variance_ratio_), 0.90) + 1),
}
dow_tab = df.groupby("dow").agg(days=("date", "size"), mean_demand_kw=("mean_demand", "mean"),
                                mean_peak_kw=("peak_demand", "mean")).round(2)
dow_tab.index = DOW
S["demand_by_dow"] = dow_tab.reset_index().to_dict("records")

# ── 3. K-Means k sweep ──────────────────────────────────────────────────────
rows = []
for k in range(2, 13):
    t0 = time.perf_counter()
    km = KMeans(n_clusters=k, random_state=42, n_init=20).fit(Xs)
    rt = time.perf_counter() - t0
    sizes = np.bincount(km.labels_)
    rows.append({"k": k, "silhouette": round(silhouette_score(Xs, km.labels_), 4),
                 "davies_bouldin": round(davies_bouldin_score(Xs, km.labels_), 4),
                 "calinski_harabasz": round(calinski_harabasz_score(Xs, km.labels_), 2),
                 "inertia": round(km.inertia_, 1), "smallest_cluster": int(sizes.min()),
                 "largest_cluster": int(sizes.max()), "fit_seconds": round(rt, 3)})
ksweep = pd.DataFrame(rows)
ksweep.to_csv(TAB / "T02_kmeans_k_sweep.csv", index=False)
S["kmeans_k_sweep"] = rows

fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
for ax, col, ttl, better in zip(axes, ["silhouette", "davies_bouldin", "inertia"],
                                ["Silhouette score", "Davies-Bouldin index", "Inertia (elbow curve)"],
                                ["higher is better", "lower is better", "within-cluster sum of squares"]):
    ax.plot(ksweep.k, ksweep[col], color=C[0], marker="o", markersize=5)
    ax.scatter([2], [ksweep[col].iloc[0]], s=70, color=C[1], zorder=3)
    ax.annotate("k = 2 (selected)", (2, ksweep[col].iloc[0]), xytext=(8, 4), textcoords="offset points", color=INK2, fontsize=8.5)
    ax.set_title(ttl)
    ax.set_xlabel(f"Number of clusters k  ({better})")
    ax.set_xticks(range(2, 13))
fig.suptitle("K-Means model selection on 1,977 standardised 96-slot daily profiles (n_init=20, random_state=42)",
             x=0.01, ha="left", fontsize=10, color=INK2)
fig.tight_layout()
save(fig, "F01_kmeans_k_selection.png")

# ── 4. clustering algorithm comparison ──────────────────────────────────────
def cmetrics(lbl, mask=None):
    if mask is not None:
        Xm, lm = Xs[mask], lbl[mask]
    else:
        Xm, lm = Xs, lbl
    if len(set(lm)) < 2:
        return None, None, None
    return (round(silhouette_score(Xm, lm), 4), round(davies_bouldin_score(Xm, lm), 4),
            round(calinski_harabasz_score(Xm, lm), 2))


rows, labels_k2 = [], {}
for k in range(2, 9):
    for name, mk in [("K-Means", lambda k: KMeans(n_clusters=k, random_state=42, n_init=20)),
                     ("Agglomerative (Ward)", lambda k: AgglomerativeClustering(n_clusters=k, linkage="ward")),
                     ("Gaussian Mixture", lambda k: GaussianMixture(n_components=k, random_state=42))]:
        t0 = time.perf_counter()
        lbl = mk(k).fit_predict(Xs)
        rt = time.perf_counter() - t0
        s, d_, c = cmetrics(lbl)
        sizes = np.bincount(lbl)
        rows.append({"model": name, "k": k, "silhouette": s, "davies_bouldin": d_, "calinski_harabasz": c,
                     "n_clusters": k, "noise_points": 0, "noise_pct": 0.0,
                     "cluster_sizes": "/".join(map(str, sorted(sizes, reverse=True))), "runtime_s": round(rt, 3)})
        if k == 2:
            labels_k2[name] = lbl
eps_knee, knee_pct = _compute_knee_eps(Xs, k=8)
t0 = time.perf_counter()
db_lbl = DBSCAN(eps=eps_knee, min_samples=8).fit_predict(Xs)
rt = time.perf_counter() - t0
ncl = len(set(db_lbl) - {-1})
s, d_, c = cmetrics(db_lbl, db_lbl != -1) if ncl >= 2 else (None, None, None)
db_row = {"model": f"DBSCAN (eps={eps_knee:.4f}, min_samples=8)", "k": None, "silhouette": s, "davies_bouldin": d_,
          "calinski_harabasz": c, "n_clusters": ncl, "noise_points": int((db_lbl == -1).sum()),
          "noise_pct": round((db_lbl == -1).mean() * 100, 2),
          "cluster_sizes": "/".join(str(int((db_lbl == c_).sum())) for c_ in sorted(set(db_lbl) - {-1})),
          "runtime_s": round(rt, 3)}
allk = pd.DataFrame(rows)
allk.to_csv(TAB / "T04_clustering_algorithms_k2_to_k8.csv", index=False)
cmp2 = pd.concat([allk[allk.k == 2], pd.DataFrame([db_row])], ignore_index=True)
for col, asc in [("silhouette", False), ("davies_bouldin", True), ("calinski_harabasz", False)]:
    cmp2[col + "_rank"] = cmp2[col].rank(ascending=asc)
cmp2["mean_rank"] = cmp2[["silhouette_rank", "davies_bouldin_rank", "calinski_harabasz_rank"]].mean(axis=1).round(3)
cmp2 = cmp2.sort_values("mean_rank", na_position="last")
cmp2.to_csv(TAB / "T03_clustering_model_comparison.csv", index=False)
S["clustering_comparison_k2"] = json.loads(cmp2.to_json(orient="records"))
km2, ag2, gm2 = labels_k2["K-Means"], labels_k2["Agglomerative (Ward)"], labels_k2["Gaussian Mixture"]
S["clustering_agreement"] = {
    "kmeans_vs_agglomerative_same_assignment_pct": round(max((km2 == ag2).mean(), (km2 != ag2).mean()) * 100, 2),
    "gmm_small_cluster_size": int(np.bincount(gm2).min()),
}

# the module's own comparison (what /api/model-comparison returns), recomputed in scratch
mc, t = timed(run_clustering_model_comparison, PROC_DIR / "daily_profiles.csv", 2, True)
saved_mc = json.load(open(BI / "models/model_comparison_cache.json"))
S["model_comparison_module"] = {
    "runtime_s": t, "best_model": mc["best_model"]["model_name"], "explanation": mc["explanation"],
    "table": mc["comparison_table"],
    "matches_saved_cache": mc["comparison_table"] == saved_mc["comparison_table"]}
_, t_cached = timed(run_clustering_model_comparison, PROC_DIR / "daily_profiles.csv", 2, False)
S["model_comparison_module"]["cached_call_s"] = t_cached

fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
m2 = cmp2[cmp2.silhouette.notna()]
for ax, col, ttl in zip(axes, ["silhouette", "davies_bouldin", "calinski_harabasz"],
                        ["Silhouette (higher is better)", "Davies-Bouldin (lower is better)", "Calinski-Harabasz (higher is better)"]):
    cols = [C[0] if m == "K-Means" else AXIS for m in m2.model]
    bars = ax.bar(m2.model, m2[col], color=cols, width=0.55)
    for b, v in zip(bars, m2[col]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:,.4g}", ha="center", va="bottom", fontsize=8.5, color=INK)
    ax.set_title(ttl)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelsize=8)
fig.suptitle("Clustering algorithms at k = 2 (selected model in blue). DBSCAN is omitted: it yields a single cluster, so the indices are undefined.",
             x=0.01, ha="left", fontsize=10, color=INK2)
fig.tight_layout()
save(fig, "F02_clustering_algorithm_comparison.png")

# ── 5. DBSCAN diagnosis ─────────────────────────────────────────────────────
def kdist(k):
    dist, _ = NearestNeighbors(n_neighbors=k + 1).fit(Xs).kneighbors(Xs)
    return np.sort(dist[:, k])


kd8 = kdist(8)
S["dbscan"] = {"eps_knee": round(eps_knee, 4), "knee_percentile": knee_pct,
               "kdist8_percentiles": {f"p{p}": round(float(np.percentile(kd8, p)), 2) for p in [10, 25, 50, 75, 90, 95, 96, 97, 98, 99, 100]},
               "noise_count": db_row["noise_points"], "n_clusters": ncl}
rows = []
for ms in [4, 8, 16]:
    kd = kdist(ms)
    eknee, kp = _compute_knee_eps(Xs, k=ms)
    cands = [(f"p{p}", float(np.percentile(kd, p))) for p in [10, 25, 50, 75, 90, 95]] + [(f"knee(p{kp})", eknee), ("p99", float(np.percentile(kd, 99)))]
    for tag, eps in cands:
        lbl = DBSCAN(eps=eps, min_samples=ms).fit_predict(Xs)
        nc = len(set(lbl) - {-1})
        noise = int((lbl == -1).sum())
        sil = round(silhouette_score(Xs[lbl != -1], lbl[lbl != -1]), 4) if nc >= 2 else None
        big = max([(lbl == c_).sum() for c_ in set(lbl) - {-1}], default=0)
        rows.append({"min_samples": ms, "eps_source": tag, "eps": round(eps, 4), "n_clusters": nc, "noise_points": noise,
                     "noise_pct": round(noise / n * 100, 2), "largest_cluster": int(big), "silhouette_non_noise": sil})
dbs = pd.DataFrame(rows)
dbs.to_csv(TAB / "T05_dbscan_eps_minsamples_sweep.csv", index=False)
S["dbscan"]["sweep_any_ge2_clusters_and_noise_lt_25pct"] = bool(((dbs.n_clusters >= 2) & (dbs.noise_pct < 25)).any())

fig, ax = plt.subplots(figsize=(7.4, 4))
ax.plot(np.arange(n) / n * 100, kd8, color=C[0])
ax.axhline(eps_knee, color=C[1], linewidth=1.2, linestyle="--")
ax.text(1, eps_knee + 1.2, f"eps = {eps_knee:.4f} (knee at the {knee_pct}th percentile)", color=INK2, fontsize=8.5)
ax.set_xlabel("Days, sorted by distance (percentile)")
ax.set_ylabel("Distance to 8th nearest neighbour")
ax.set_title("DBSCAN k-distance curve (k = min_samples = 8)")
ax.set_xlim(0, 100)
save(fig, "F03_dbscan_k_distance.png")

# ── 6. cluster profiles (final K-Means, k=2) ────────────────────────────────
rows = []
for cid in sorted(df.kmeans_cluster.unique()):
    sub = df[df.kmeans_cluster == cid]
    mp = sub[PCOLS].mean().values
    r = {"cluster": int(cid), "days": len(sub), "share_pct": round(len(sub) / n * 100, 2),
         "mean_demand_kw": round(sub.mean_demand.mean(), 2), "mean_peak_kw": round(sub.peak_demand.mean(), 2),
         "mean_min_kw": round(sub.min_demand.mean(), 2), "mean_intraday_std_kw": round(sub.std_demand.mean(), 2),
         "peak_time_of_mean_profile": f"{int(mp.argmax()) // 4:02d}:{int(mp.argmax()) % 4 * 15:02d}",
         "trough_time_of_mean_profile": f"{int(mp.argmin()) // 4:02d}:{int(mp.argmin()) % 4 * 15:02d}",
         "weekend_pct": round(sub.is_weekend.mean() * 100, 2), "anomaly_days": int(sub.final_is_anomaly.sum())}
    for i, dname in enumerate(DOW):
        r[dname] = int((sub.dow == i).sum())
    for l in LABELS:
        r[l] = int((sub.behavior_label == l).sum())
    rows.append(r)
cprof = pd.DataFrame(rows)
cprof.to_csv(TAB / "T06_kmeans_cluster_profiles.csv", index=False)
S["cluster_profiles"] = rows
S["cluster_vs_weekend"] = pd.crosstab(df.kmeans_cluster, df.is_weekend).to_dict()
pd.crosstab(df.kmeans_cluster, df.month).to_csv(TAB / "T07_kmeans_cluster_by_month.csv")
# how well does cluster == weekend?
wk_cluster = int(df.groupby("kmeans_cluster").is_weekend.mean().idxmax())
S["cluster_weekend_alignment"] = {
    "weekend_like_cluster": wk_cluster,
    "agreement_pct": round(((df.kmeans_cluster == wk_cluster) == df.is_weekend).mean() * 100, 2)}

fig, ax = plt.subplots(figsize=(8.2, 4.2))
for cid, col in zip(sorted(df.kmeans_cluster.unique()), C):
    sub = df[df.kmeans_cluster == cid][PCOLS]
    ax.fill_between(HOURS, sub.quantile(.25), sub.quantile(.75), color=col, alpha=0.18, linewidth=0)
    ax.plot(HOURS, sub.mean(), color=col, label=f"Cluster {cid}  ({len(sub):,} days, {cprof.weekend_pct[cid]:.0f}% weekend days)")
ax.set_ylabel("Load demand (kW)")
ax.set_title("Mean daily load shape of the two K-Means clusters (band = inter-quartile range)")
hour_axis(ax)
ax.legend(loc="upper left")
save(fig, "F04_kmeans_cluster_profiles.png")

pcs = PCA(n_components=2, random_state=42).fit_transform(Xs)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
iso_mask = df.final_is_anomaly.values.astype(bool)
for ax, zoom in zip(axes, [False, True]):
    for cid, col in zip(sorted(df.kmeans_cluster.unique()), C):
        m = (df.kmeans_cluster.values == cid) & ~iso_mask
        ax.scatter(pcs[m, 0], pcs[m, 1], s=9, color=col, alpha=0.55, linewidths=0, label=f"Cluster {cid}")
    ax.scatter(pcs[iso_mask, 0], pcs[iso_mask, 1], s=26, facecolors="none", edgecolors=C[7], linewidths=1.1,
               label="Isolation Forest anomaly (60 days)")
    ax.set_xlabel(f"PC1 ({pca_full.explained_variance_ratio_[0] * 100:.1f}% of variance)")
    ax.set_ylabel(f"PC2 ({pca_full.explained_variance_ratio_[1] * 100:.1f}% of variance)")
    if zoom:
        q = np.percentile(pcs[~iso_mask], [0.5, 99.5], axis=0)
        ax.set_xlim(q[0, 0] - 1, q[1, 0] + 1)
        ax.set_ylim(q[0, 1] - 1, q[1, 1] + 1)
        ax.set_title("Zoomed to the non-anomalous days")
    else:
        ax.set_title("All 1,977 days in the first two principal components")
        ax.legend(loc="best", fontsize=8.5)
fig.tight_layout()
save(fig, "F05_pca_clusters_and_anomalies.png")

# ── 7. anomaly detection comparison ─────────────────────────────────────────
det = {}
for name, fn, args in [("Isolation Forest", ac._run_isolation_forest, (Xs, 0.03)),
                       ("Local Outlier Factor", ac._run_lof, (Xs, 0.03)),
                       ("One-Class SVM", ac._run_one_class_svm, (Xs, 0.03)),
                       ("Z-Score (|z|>=3.0)", ac._run_zscore, (df,))]:
    (m, flags, score), rt = timed(fn, *args)
    det[name] = {"flags": np.asarray(flags), "score": np.asarray(score), "runtime_s": rt, "metrics": m}
det["DBSCAN noise (knee eps)"] = {"flags": db_lbl == -1, "score": None, "runtime_s": db_row["runtime_s"], "metrics": {}}
det["GMM minority component (k=2)"] = {"flags": gm2 == np.bincount(gm2).argmin(), "score": None, "runtime_s": None, "metrics": {}}
names = list(det)
inter = pd.DataFrame(index=names, columns=names, dtype=float)
jac = pd.DataFrame(index=names, columns=names, dtype=float)
for a in names:
    for b in names:
        A, B = det[a]["flags"], det[b]["flags"]
        inter.loc[a, b] = int((A & B).sum())
        jac.loc[a, b] = round((A & B).sum() / max((A | B).sum(), 1), 4)
inter.astype(int).to_csv(TAB / "T09_anomaly_flag_overlap_counts.csv")
jac.to_csv(TAB / "T10_anomaly_flag_overlap_jaccard.csv")
S["anomaly_overlap_counts"] = inter.astype(int).to_dict()
S["anomaly_overlap_jaccard"] = jac.to_dict()

# module's own comparison (bootstrap stability) recomputed in scratch
acmp, t = timed(ac.run_anomaly_detection_comparison, PROC_DIR / "daily_profiles.csv", 0.03, 20, 0.8, True)
saved_ac = json.load(open(BI / "models/anomaly_comparison_cache.json"))
_, t_cached = timed(ac.run_anomaly_detection_comparison, PROC_DIR / "daily_profiles.csv", 0.03, 20, 0.8, False)
S["anomaly_comparison_module"] = {
    "runtime_s_reported": acmp["runtime_seconds"], "wall_s": t, "cached_call_s": t_cached,
    "best_model": acmp["best_model"]["model_name"], "explanation": acmp["explanation"],
    "table": acmp["comparison_table"], "spearman": acmp["spearman_matrix"],
    "table_matches_saved_cache": acmp["comparison_table"] == saved_ac["comparison_table"],
    "spearman_matches_saved_cache": acmp["spearman_matrix"] == saved_ac["spearman_matrix"],
    "saved_cache_runtime_s": saved_ac["runtime_seconds"]}
# per-resample check: do Isolation Forest and LOF flag the identical set in every resample?
same_sets, per = 0, []
prof_df = pd.read_csv(PROC_DIR / "daily_profiles.csv")
full = {k: set(np.where(det[k]["flags"])[0]) for k in ["Isolation Forest", "Local Outlier Factor", "One-Class SVM"]}
for seed in range(20):
    idx = np.sort(np.random.default_rng(seed).choice(n, size=int(0.8 * n), replace=False))
    _, f_if, _ = ac._run_isolation_forest(Xs[idx], 0.03)
    _, f_lof, _ = ac._run_lof(Xs[idx], 0.03)
    _, f_svm, _ = ac._run_one_class_svm(Xs[idx], 0.03)
    a, b, c_ = set(idx[f_if]), set(idx[f_lof]), set(idx[f_svm])
    same_sets += a == b
    per.append({"seed": seed, "if_flagged": len(a), "lof_flagged": len(b), "svm_flagged": len(c_),
                "if_equals_lof": a == b,
                "if_jaccard_vs_full": round(len(a & full["Isolation Forest"]) / len(a | full["Isolation Forest"]), 4),
                "lof_jaccard_vs_full": round(len(b & full["Local Outlier Factor"]) / len(b | full["Local Outlier Factor"]), 4),
                "svm_jaccard_vs_full": round(len(c_ & full["One-Class SVM"]) / len(c_ | full["One-Class SVM"]), 4),
                "full_if_anomalies_in_sample": int(np.isin(sorted(full["Isolation Forest"]), idx).sum())})
pd.DataFrame(per).to_csv(TAB / "T11_bootstrap_stability_per_resample.csv", index=False)
S["bootstrap_if_equals_lof_in_resamples"] = f"{same_sets}/20"
S["bootstrap_mean_full_if_anomalies_in_sample"] = round(float(np.mean([p["full_if_anomalies_in_sample"] for p in per])), 2)

rows = []
for r in acmp["comparison_table"]:
    key = "Z-Score (|z|>=3.0)" if r["model"] == "Z-Score" else r["model"]
    rows.append({**r, "runtime_s_single_fit": det[key]["runtime_s"],
                 "overlap_with_isolation_forest": int(inter.loc[key, "Isolation Forest"])})
pd.DataFrame(rows).to_csv(TAB / "T08_anomaly_model_comparison.csv", index=False)
sp = pd.DataFrame(acmp["spearman_matrix"])
sp.to_csv(TAB / "T12_anomaly_score_spearman.csv")

# z-score diagnostics
pz = np.abs(stats.zscore(df.peak_demand))
mz = np.abs(stats.zscore(df.mean_demand))
S["zscore"] = {"max_abs_peak_z": round(float(pz.max()), 3), "max_abs_mean_z": round(float(mz.max()), 3),
               "flags_by_threshold": {str(t_): int(((pz >= t_) | (mz >= t_)).sum()) for t_ in [3.0, 2.5, 2.0, 1.5]},
               "days_above_mean_plus_1.5std_peak": int((stats.zscore(df.peak_demand) > 1.5).sum()),
               "days_above_mean_plus_1.5std_mean": int((stats.zscore(df.mean_demand) > 1.5).sum()),
               "peak_zscore_gt_2_signed_abs": int((df.peak_zscore > 2.0).sum())}

fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
t_ = pd.DataFrame(acmp["comparison_table"])
cols = [C[0] if s_ == "Best Model" else AXIS for s_ in t_.status]
for ax, col, ttl in zip(axes, ["mean_jaccard", "mean_symmetric_difference"],
                        ["Mean Jaccard vs full-data flagged set (higher = more stable)",
                         "Mean symmetric difference in days (lower = more stable)"]):
    bars = ax.bar(t_.model, t_[col], color=cols, width=0.55)
    for b, v in zip(bars, t_[col]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:g}", ha="center", va="bottom", fontsize=8.5, color=INK)
    ax.set_title(ttl, fontsize=10)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelsize=8.5)
fig.suptitle("Bootstrap stability of anomaly detectors: 20 resamples of 80% of days, seeds 0-19 (Z-Score flags 0 days and is not ranked)",
             x=0.01, ha="left", fontsize=10, color=INK2)
fig.tight_layout()
save(fig, "F06_anomaly_bootstrap_stability.png")

fig, ax = plt.subplots(figsize=(7.6, 3.9))
sc = df.isolation_anomaly_score
bins = np.linspace(sc.min(), sc.max(), 60)
ax.hist(sc[~iso_mask], bins=bins, color=C[0], label=f"Not flagged ({(~iso_mask).sum():,} days)")
ax.hist(sc[iso_mask], bins=bins, color=C[7], label=f"Flagged as anomaly ({iso_mask.sum()} days)")
ax.axvline(0, color=INK2, linewidth=1, linestyle="--")
ax.text(0.005, ax.get_ylim()[1] * 0.92, "decision threshold (score = 0)", fontsize=8.5, color=INK2)
ax.set_xlabel("Isolation Forest anomaly score (negated decision function; higher = more anomalous)")
ax.set_ylabel("Days")
ax.set_title("Distribution of Isolation Forest anomaly scores")
ax.legend()
save(fig, "F07_isolation_forest_score_distribution.png")

# anomaly day catalogue
med_profile = df.loc[~iso_mask, PCOLS].median().values
an = df[iso_mask].copy()
an["max_ratio_to_median_profile"] = (an[PCOLS].values / med_profile).max(axis=1).round(2)
an["min_ratio_to_median_profile"] = (an[PCOLS].values / med_profile).min(axis=1).round(2)
an["slots_above_1.5x_median"] = (an[PCOLS].values > 1.5 * med_profile).sum(axis=1)
an["slots_below_0.7x_median"] = (an[PCOLS].values < 0.7 * med_profile).sum(axis=1)
an["longest_run_above_1.5x"] = [max((len(r) for r in "".join("1" if v else "0" for v in row).split("0")), default=0)
                                for row in (an[PCOLS].values > 1.5 * med_profile)]
an["day_of_week"] = an.dow.map(dict(enumerate(DOW)))
an["flagged_by_lof"] = det["Local Outlier Factor"]["flags"][iso_mask]
an["flagged_by_ocsvm"] = det["One-Class SVM"]["flags"][iso_mask]
an["dbscan_noise"] = (db_lbl == -1)[iso_mask]
cat = an[["date", "day_of_week", "peak_demand", "mean_demand", "min_demand", "std_demand", "isolation_anomaly_score",
          "peak_zscore", "mean_zscore", "max_ratio_to_median_profile", "min_ratio_to_median_profile",
          "slots_above_1.5x_median", "slots_below_0.7x_median", "longest_run_above_1.5x", "kmeans_cluster",
          "is_peak_demand_day", "behavior_label", "flagged_by_lof", "flagged_by_ocsvm", "dbscan_noise"]].copy()
cat["date"] = cat.date.dt.strftime("%Y-%m-%d")
cat = cat.sort_values("isolation_anomaly_score", ascending=False).round(3)
cat.to_csv(TAB / "T13_anomaly_days_catalogue.csv", index=False)
S["anomaly_days"] = {
    "count": int(iso_mask.sum()),
    "by_year": an.year.value_counts().sort_index().to_dict(),
    "by_dow": {DOW[k]: int(v) for k, v in an.dow.value_counts().sort_index().items()},
    "by_month": {int(k): int(v) for k, v in an.month.value_counts().sort_index().items()},
    "by_label": an.behavior_label.value_counts().to_dict(),
    "spike_like(any slot >1.5x median)": int((an["slots_above_1.5x_median"] > 0).sum()),
    "dip_like(any slot <0.7x median)": int((an["slots_below_0.7x_median"] > 0).sum()),
    "both": int(((an["slots_above_1.5x_median"] > 0) & (an["slots_below_0.7x_median"] > 0)).sum()),
    "neither": int(((an["slots_above_1.5x_median"] == 0) & (an["slots_below_0.7x_median"] == 0)).sum()),
    "longest_run_above_1.5x_describe": an["longest_run_above_1.5x"].describe().round(2).to_dict(),
    "non_anomalous_days_with_any_slot_above_1.5x_median": int(((df.loc[~iso_mask, PCOLS].values > 1.5 * med_profile).any(axis=1)).sum()),
    "non_anomalous_days_with_any_slot_below_0.7x_median": int(((df.loc[~iso_mask, PCOLS].values < 0.7 * med_profile).any(axis=1)).sum()),
    "top10": cat.head(10)[["date", "day_of_week", "peak_demand", "mean_demand", "isolation_anomaly_score", "behavior_label"]].to_dict("records"),
    "min_score_flagged": round(float(sc[iso_mask].min()), 4), "max_score_unflagged": round(float(sc[~iso_mask].max()), 4),
}

top = cat.head(6)
fig, axes = plt.subplots(2, 3, figsize=(12, 5.6), sharex=True, sharey=True)
for ax, (_, r) in zip(axes.ravel(), top.iterrows()):
    row = df[df.date == r.date].iloc[0]
    ax.plot(HOURS, med_profile, color=AXIS, label="Median non-anomalous day")
    ax.plot(HOURS, row[PCOLS].values.astype(float), color=C[7], label="Anomalous day")
    ax.set_title(f"{r.date} ({r.day_of_week}) · score {r.isolation_anomaly_score:.3f}\nlabelled: {r.behavior_label}", fontsize=9)
for ax in axes[1]:
    ax.set_xticks(range(0, 25, 6))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 6)])
    ax.set_xlim(0, 24)
for ax in axes[:, 0]:
    ax.set_ylabel("Load demand (kW)")
h_, l_ = axes[0, 0].get_legend_handles_labels()
fig.legend(h_, l_, loc="upper right", ncol=2, fontsize=8.5, bbox_to_anchor=(0.99, 1.0))
fig.suptitle("The six highest-scoring Isolation Forest anomaly days against the median load shape",
             x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.97))
save(fig, "F08_top_anomaly_day_profiles.png")

# ── 8. peak detection ───────────────────────────────────────────────────────
t90, t75 = df.peak_demand.quantile(.90), df.peak_demand.quantile(.75)
c90 = df.peak_demand >= t90
cz = df.peak_zscore > 2.0
ca = df.final_is_anomaly.astype(bool) & (df.peak_demand >= t75)
S["peak"] = {"threshold_90": round(float(t90), 2), "threshold_75": round(float(t75), 2),
             "cond_90_days": int(c90.sum()), "cond_zscore_gt2_days": int(cz.sum()), "cond_anomaly_and_75_days": int(ca.sum()),
             "zscore_only_days": int((cz & ~c90 & ~ca).sum()), "anomaly75_only_days": int((ca & ~c90).sum()),
             "cond90_and_anomaly": int((c90 & df.final_is_anomaly.astype(bool)).sum()),
             "peak_days_total": int(df.is_peak_demand_day.sum()), "peak_pct": round(df.is_peak_demand_day.mean() * 100, 2),
             "zscore_gt2_days_with_peak_below_mean": int((cz & (df.peak_demand < df.peak_demand.mean())).sum()),
             "peak_days_by_dow": {DOW[k]: int(v) for k, v in df[df.is_peak_demand_day].dow.value_counts().sort_index().items()},
             "peak_days_weekend_pct": round(df[df.is_peak_demand_day].is_weekend.mean() * 100, 2),
             "min_peak_kw_among_peak_days": round(float(df[df.is_peak_demand_day].peak_demand.min()), 2)}
pd.DataFrame([{"condition": "peak_demand >= 90th percentile", "threshold": round(t90, 2), "days": int(c90.sum())},
              {"condition": "peak_zscore > 2.0 (absolute z-score)", "threshold": 2.0, "days": int(cz.sum())},
              {"condition": "final_is_anomaly AND peak_demand >= 75th percentile", "threshold": round(t75, 2), "days": int(ca.sum())},
              {"condition": "ANY (is_peak_demand_day)", "threshold": None, "days": int(df.is_peak_demand_day.sum())}]
             ).to_csv(TAB / "T15_peak_detection_conditions.csv", index=False)

fig, ax = plt.subplots(figsize=(7.6, 3.9))
bins = np.linspace(df.peak_demand.min(), df.peak_demand.max(), 70)
ax.hist(df.peak_demand[~df.is_peak_demand_day], bins=bins, color=C[0], label=f"Not a peak day ({(~df.is_peak_demand_day).sum():,})")
ax.hist(df.peak_demand[df.is_peak_demand_day], bins=bins, color=C[1], label=f"Peak demand day ({df.is_peak_demand_day.sum()})")
for v, lab_ in [(t75, f"75th pct = {t75:,.0f} kW"), (t90, f"90th pct = {t90:,.0f} kW")]:
    ax.axvline(v, color=INK2, linewidth=1, linestyle="--")
    ax.text(v, ax.get_ylim()[1] * 0.97, " " + lab_, fontsize=8.5, color=INK2, va="top", rotation=90, ha="right")
ax.set_xlabel("Daily peak demand (kW)")
ax.set_ylabel("Days")
ax.set_title("Daily peak demand and the peak-day thresholds")
ax.legend(loc="upper right")
save(fig, "F09_peak_demand_thresholds.png")

# ── 9. behaviour labels ─────────────────────────────────────────────────────
low_thr = df.mean_demand.quantile(.25)
S["labels"] = {"low_demand_threshold_kw": round(float(low_thr), 2),
               "counts": df.behavior_label.value_counts().to_dict(),
               "pct": (df.behavior_label.value_counts(normalize=True) * 100).round(2).to_dict(),
               "risk": df.behavior_risk_level.value_counts().to_dict(),
               "normal_weekday_label_on_weekend_days": int(((df.behavior_label == LABELS[0]) & df.is_weekend).sum()),
               "holiday_low_label_on_weekdays": int(((df.behavior_label == LABELS[2]) & ~df.is_weekend).sum()),
               "holiday_low_label_on_weekends": int(((df.behavior_label == LABELS[2]) & df.is_weekend).sum()),
               "anomalies_relabelled_as_peak": int((df.final_is_anomaly.astype(bool) & (df.behavior_label == LABELS[1])).sum()),
               "abnormal_days": int((df.behavior_label == LABELS[3]).sum())}
by_dow = pd.crosstab(df.dow, df.behavior_label).reindex(columns=LABELS, fill_value=0)
by_dow.index = DOW
by_dow.to_csv(TAB / "T16_behaviour_label_by_day_of_week.csv")
by_month = pd.crosstab(df.month, df.behavior_label).reindex(columns=LABELS, fill_value=0)
by_month.to_csv(TAB / "T17_behaviour_label_by_month.csv")
by_year = pd.crosstab(df.year, df.behavior_label).reindex(columns=LABELS, fill_value=0)
by_year.to_csv(TAB / "T18_behaviour_label_by_year.csv")
x_cl = pd.crosstab(df.behavior_label, df.kmeans_cluster).reindex(LABELS)
x_cl.to_csv(TAB / "T19_behaviour_label_vs_kmeans_cluster.csv")
dist = pd.DataFrame({"behavior_label": LABELS,
                     "risk_level": ["Normal", "Medium", "Low", "High"],
                     "days": [int((df.behavior_label == l).sum()) for l in LABELS]})
dist["percent"] = (dist.days / n * 100).round(2)
dist["mean_demand_kw"] = [round(df[df.behavior_label == l].mean_demand.mean(), 2) for l in LABELS]
dist["mean_peak_kw"] = [round(df[df.behavior_label == l].peak_demand.mean(), 2) for l in LABELS]
dist["weekend_pct"] = [round(df[df.behavior_label == l].is_weekend.mean() * 100, 2) for l in LABELS]
dist.to_csv(TAB / "T20_behaviour_label_distribution.csv", index=False)
S["labels"]["distribution_table"] = dist.to_dict("records")
S["labels"]["by_dow"] = by_dow.to_dict("index")
S["labels"]["vs_cluster"] = x_cl.to_dict("index")

fig, axes = plt.subplots(1, 2, figsize=(12, 3.9), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axes[0]
bars = ax.barh(dist.behavior_label[::-1], dist.days[::-1], color=[LABEL_COLOR[l] for l in dist.behavior_label[::-1]], height=0.6)
for b, d_, p_ in zip(bars, dist.days[::-1], dist.percent[::-1]):
    ax.text(b.get_width() + 15, b.get_y() + b.get_height() / 2, f"{d_:,} days ({p_:.2f}%)", va="center", fontsize=9, color=INK)
ax.set_xlim(0, dist.days.max() * 1.35)
ax.grid(axis="y", visible=False)
ax.set_xlabel("Days")
ax.set_title("Behaviour label distribution (1,977 days)")
ax = axes[1]
share = by_dow.div(by_dow.sum(axis=1), axis=0) * 100
bottom = np.zeros(7)
for l in LABELS:
    ax.bar(DOW, share[l], bottom=bottom, color=LABEL_COLOR[l], label=l, width=0.62, edgecolor=SURF, linewidth=1.5)
    bottom += share[l].values
ax.set_ylabel("Share of days (%)")
ax.set_ylim(0, 100)
ax.grid(axis="x", visible=False)
ax.set_title("Label mix by day of week")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8.5)
fig.tight_layout()
save(fig, "F10_behaviour_label_distribution.png")

fig, ax = plt.subplots(figsize=(8.2, 4.2))
for l in LABELS:
    sub = df[df.behavior_label == l][PCOLS]
    ax.plot(HOURS, sub.mean(), color=LABEL_COLOR[l], label=f"{l} (n={len(sub):,})")
ax.set_ylabel("Load demand (kW)")
ax.set_title("Mean daily load shape by behaviour label")
hour_axis(ax)
ax.legend(loc="upper left", fontsize=8.5)
save(fig, "F11_mean_profile_by_behaviour_label.png")

ym = pd.crosstab([df.year, df.month], df.behavior_label).reindex(columns=LABELS, fill_value=0)
ym_share = ym.div(ym.sum(axis=1), axis=0) * 100
xs = np.arange(len(ym))
fig, ax = plt.subplots(figsize=(12, 3.8))
bottom = np.zeros(len(ym))
for l in LABELS:
    ax.bar(xs, ym_share[l], bottom=bottom, color=LABEL_COLOR[l], label=l, width=0.9)
    bottom += ym_share[l].values
ticks = [i for i, (y, m) in enumerate(ym.index) if m == 1]
ax.set_xticks(ticks)
ax.set_xticklabels([str(ym.index[i][0]) for i in ticks])
ax.set_xlim(-0.6, len(ym) - 0.4)
ax.set_ylim(0, 100)
ax.set_ylabel("Share of days (%)")
ax.set_xlabel("Month (tick = January of each year)")
ax.grid(axis="x", visible=False)
ax.set_title("Monthly behaviour-label mix, January 2020 to May 2025")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4, fontsize=8.5)
save(fig, "F12_monthly_behaviour_label_mix.png")

fig, ax = plt.subplots(figsize=(8.2, 4.2))
wd = df[~df.is_weekend][PCOLS]
we = df[df.is_weekend][PCOLS]
for sub, col, name in [(wd, C[0], "Weekdays (Mon-Fri)"), (we, C[1], "Weekend days (Sat-Sun)")]:
    ax.fill_between(HOURS, sub.quantile(.25), sub.quantile(.75), color=col, alpha=0.18, linewidth=0)
    ax.plot(HOURS, sub.mean(), color=col, label=f"{name}, n={len(sub):,}")
ax.set_ylabel("Load demand (kW)")
ax.set_title("Dataset structure: mean daily load shape, weekdays vs weekend days (band = IQR)")
hour_axis(ax)
ax.legend(loc="upper left")
save(fig, "F13_dataset_weekday_vs_weekend_profile.png")

# ── 10. prediction module back-test (temporal hold-out) ─────────────────────
cut = pd.Timestamp("2024-06-01")
lab_all = df[["date", "behavior_label"]].copy()
train, test = lab_all[lab_all.date < cut], lab_all[lab_all.date >= cut]
tr_path = WS / "train_labels.csv"
train.assign(date=train.date.dt.strftime("%Y-%m-%d")).to_csv(tr_path, index=False)
t0 = time.perf_counter()
preds = [predict_future_behavior(tr_path, d_.strftime("%Y-%m-%d")) for d_ in test.date]
bt_time = time.perf_counter() - t0
pred_lbl = np.array([p["predicted_label"] for p in preds])
conf = np.array([p["confidence_percent"] for p in preds])
truth = test.behavior_label.values
maj = train.behavior_label.value_counts().idxmax()
rows = []
for l in LABELS:
    tp = int(((pred_lbl == l) & (truth == l)).sum())
    fp = int(((pred_lbl == l) & (truth != l)).sum())
    fn = int(((pred_lbl != l) & (truth == l)).sum())
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    rows.append({"label": l, "support": int((truth == l).sum()), "predicted": int((pred_lbl == l).sum()),
                 "precision": round(pr, 4), "recall": round(rc, 4), "f1": round(2 * pr * rc / (pr + rc), 4) if pr + rc else 0.0})
bt = pd.DataFrame(rows)
bt.to_csv(TAB / "T21_prediction_backtest_per_label.csv", index=False)
pd.crosstab(pd.Series(truth, name="actual"), pd.Series(pred_lbl, name="predicted")).to_csv(TAB / "T22_prediction_backtest_confusion.csv")
S["prediction_backtest"] = {
    "note": "computed by this script; not part of the component code base",
    "cutoff": str(cut.date()), "train_days": len(train), "test_days": len(test),
    "accuracy_pct": round((pred_lbl == truth).mean() * 100, 2),
    "majority_baseline_label": maj, "majority_baseline_accuracy_pct": round((truth == maj).mean() * 100, 2),
    "macro_f1": round(bt.f1.mean(), 4), "mean_confidence_pct": round(float(conf.mean()), 2),
    "strategies_used": pd.Series([p["match_strategy"] for p in preds]).value_counts().to_dict(),
    "mean_matched_days": round(float(np.mean([p["matched_days_count"] for p in preds])), 1),
    "per_label": rows, "mean_ms_per_prediction": round(bt_time / len(test) * 1000, 2)}

S["figures"] = FIGS
json.dump(S, open(TAB / "eval_summary.json", "w"), indent=2, default=str)
print(json.dumps(S, indent=1, default=str))
