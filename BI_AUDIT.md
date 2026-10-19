# Audit — Behaviour Intelligence (IT22545176, Thanujan)

**Audit date:** 2026-10-19 · **Viva:** 20 Oct 2026

**Code audited:** `behaviour-intelligence/`, branch `backup-thanujan-oct18`, commit `059587a`, working tree clean.

**Mode:** read-only. No project file was created, changed or deleted, apart from this report. The recomputation ran from the session scratchpad with `behaviour-intelligence/.venv` (Python 3.12.7, sklearn 1.4.2, the version the saved `.pkl` files were made with). The smoke test used only GET requests against the BI backend that was already running on port 8001. A marker-file check confirmed that **no file in `data/` or `models/` changed** during any check.

PP2 panel comments:
1. "Have done a model comparison, but moderate idea about clustering"
2. "Needs to have a clear idea on why the models have selected, and on what considerations"
3. "Parameters used, why?"
4. "Need to use fine-tuning techniques"

> **Most important new finding: the dataset has a recoverable ground truth.**
>
> `notebooks/06_model_comparison.ipynb` **cell 14 generated** `data/raw/synthetic_realistic_load.csv`. Re-running that code reproduces the file exactly (189,793 rows, max difference 0.0 kW). The generator builds:
> - a fixed daily shape: night trough, morning bump at 08:00, evening peak at 19:30;
> - weekends at 82% of weekday level;
> - ±8% seasonality, peaking in June;
> - 4% random noise;
> - **60 deliberately injected anomaly days** (seed 42).
>
> So, for the first time, BI's models can be scored against known truth. Results:
> - **Isolation Forest finds exactly the 60 injected days:** precision 1.0, recall 1.0.
> - **DBSCAN's 60 noise points are exactly the same 60 days.**
> - **K-Means k=2 is exactly weekday vs weekend:** ARI 0.965, and 1.000 once the injected days are excluded.
>
> The earlier evidence pack (`THESIS_EVIDENCE_IT22545176.md`, 10 Oct) says "no ground truth", because notebook 06 was empty then (filled on 16 Oct). This is the strongest answer available for panel comments 1, 2 and 4, but it must be presented honestly (see §7.3).

---

## 1. Component overview

### 1.1 What BI does

| | |
|---|---|
| **Problem** | Planners need to know what *kind* of day each day is (normal, peak, low, abnormal), which days are unusual, and what to expect on a future date. |
| **Input** | `data/raw/synthetic_realistic_load.csv` (`backend/app/core/config.py:11`) |
| **Output** | One label + risk level per day (`data/processed/behavior_labels.csv`), anomaly scores, cluster IDs, model comparisons, a future-date prediction, a REST API (port 8001) and a React dashboard (port 3000) |

### 1.2 Dataset

| Item | Value (verified) |
|---|---|
| File | `data/raw/synthetic_realistic_load.csv` (7.5 MB, created 2026-08-25 by notebook 06 cell 14) |
| Rows | 189,793 at 15-minute intervals |
| Range | 2020-01-01 00:00 → 2025-05-31 00:00 (the last day has a single reading, so it is dropped) |
| Columns | `Timestamp`, `Load Demand (kW)`, `Temperature (°C)`, `Solar Irradiance (W/m²)`. **Only `Load Demand` is used**; temperature and solar are never read by the pipeline |
| Missing values | 0 |
| Generator | `load = 2200 × shape(hour) × weekend(0.82 if Sat/Sun) × seasonal(1 + 0.08·sin(2π(month−3)/12)) × N(1, 0.04)`; then 60 random days have **each reading** multiplied by 0.55 or 1.45 (50.5% got ×1.45), which makes those days jagged |
| Holidays | **None in the data.** The label "Holiday / Low Demand Day" therefore detects weekends (§4.2) |

### 1.3 Folder and file map

| Path | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI app, CORS for `localhost:3000` and `3001` (line 15), `/health` |
| `backend/app/api/routes.py` | 11 routes under `/api` |
| `backend/app/controllers/pipeline_controller.py` | Calls the ML modules; wraps errors as `{"success": false}` |
| `backend/app/services/analysis_service.py` | Dashboard summary and day-profile payloads |
| `backend/app/core/config.py` | Paths, dataset name, port 8001 |
| `backend/app/ml/data_loader.py` | Load CSV with explicit column names |
| `backend/app/ml/preprocessing.py` | Cleaning, 15-min resampling, helper columns |
| `backend/app/ml/daily_profile.py` | 96-slot daily profiles |
| `backend/app/ml/clustering.py` | **Production** K-Means (auto-k) + DBSCAN (knee eps) |
| `backend/app/ml/anomaly_detection.py` | **Production** Isolation Forest + z-score diagnostics |
| `backend/app/ml/peak_detection.py` | Peak-day rules |
| `backend/app/ml/behavior_labeling.py` | Priority rules → label + risk |
| `backend/app/ml/behavior_prediction.py` | Future-date label by historical frequency |
| `backend/app/ml/model_comparison.py` | K-Means vs DBSCAN vs Ward vs GMM (cached) |
| `backend/app/ml/anomaly_comparison.py` | Isolation Forest vs z-score vs One-Class SVM vs LOF, bootstrap stability (cached) |
| `backend/app/ml/pipeline_runner.py` | Runs the five stages end to end |
| `backend/app/ml/train_models.py` | **Old, drifted** training script. Do **not** run: it differs from the API modules (§9.2) and would overwrite outputs |
| `backend/app/ml/verify_pkl_models.py` | Loads each `.pkl` and prints its type and settings |
| `data/processed/*.csv` | Pipeline outputs (Sep 1 2026); `*_OLD` = May run on the old dataset |
| `models/*.pkl`, `*.json` | Saved models, metrics and comparison caches |
| `notebooks/01–06` | 01 never executed; 02–05 from May (old run); **06 generated the dataset** and holds the exploratory comparison |
| `reports/` | **Stale** (Aug 25, old dataset): see §9.2 |
| `frontend/src/App.jsx` | Dashboard (Vite, `main.jsx` → `App.jsx`) |
| `frontend/src/ModelComparison.jsx`, `AnomalyComparison.jsx` | The two comparison pages |
| `frontend/src/FutureBehaviorPrediction.jsx` | Future prediction panel |
| `frontend/src/TeammateComponentView.jsx`, `components.config.js` | Teammate apps in iframes after a reachability check |
| `frontend/src/App.js`, `index.js`, `FutureBehaviorPrediction.js`, `frontend/build/` | **Unused legacy** CRA files |
| `test_zscore_thresholds.py` | A print script, not a test |

### 1.4 Pipeline (as implemented, `pipeline_runner.py:13-90`)

```
synthetic_realistic_load.csv (189,793 readings)
 └─ preprocessing.py
      drop NaN/negative (0 removed)
      drop > median + 10×IQR = 5,190.72 kW (0 removed)
      interpolate gaps
      drop outside Q1−3×IQR … Q3+3×IQR = [485.49, 2,928.49] kW  → 691 HIGH readings removed (0 low)
      resample to 15 min + interpolate → 189,793 rows → cleaned_data.csv
 └─ daily_profile.py: pivot to 96 slots (p00…p95), keep complete days → 1,977 days (2020-01-01 … 2025-05-30)
      + peak_demand, mean_demand, std_demand per day → daily_profiles.csv
 └─ clustering.py: StandardScaler (per slot, across days) → K-Means (k by silhouette over 2–12) + DBSCAN (eps = k-distance knee)
      → clustering_results.csv, kmeans/dbscan/scaler .pkl, clustering_metrics.json
 └─ anomaly_detection.py: Isolation Forest (300 trees, contamination 0.03) on the scaled profiles
      final_is_anomaly = Isolation Forest only; z-scores kept as diagnostics → anomaly_results.csv
 └─ peak_detection.py: peak if peak ≥ p90 OR |z(peak)| > 2 OR (anomaly AND peak ≥ p75) → peak_demand_results.csv
 └─ behavior_labeling.py: Abnormal → Peak → Holiday/Low → Normal, with risk High/Medium/Low/Normal → behavior_labels.csv
 └─ behavior_prediction.py (on request): month+weekday frequency → month → all history
 └─ FastAPI (8001) → React dashboard (3000) → "LIME →" button → XAI app (5173)
```

### 1.5 Connections and how to run

| Item | Value |
|---|---|
| Start everything | `python start-all.py` (workspace root). BI backend uses `behaviour-intelligence/.venv` (fixed 18 Oct) |
| Backend (manual) | in `behaviour-intelligence/backend`: `..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001` |
| Frontend | in `behaviour-intelligence/frontend`: `npm run dev` or `npm start` (both Vite, port 3000) |
| XAI link | `App.jsx:17-24`, `FutureBehaviorPrediction.jsx:18-31` open `http://localhost:5173/anomaly-diagnosis?source=bi&date=YYYY-MM-DD` |
| Teammate iframes | `components.config.js`: forecast `5175`, XAI `5173`, NN `5176` |
| **README run command is wrong** | `README.md:256` `python -m uvicorn backend.app.main:app` fails with `ModuleNotFoundError: No module named 'app'` (verified) |

---

## 2. Clustering (PP2 comment 1)

### 2.1 Methods and where they are

| Method | Role | File / function |
|---|---|---|
| StandardScaler | scale each of the 96 slots across days | `clustering.py:121-122` |
| **K-Means** | production clustering | `clustering.py:34-46` `_select_best_k`, `:126-127` |
| **DBSCAN** | production (reported as degenerate) | `clustering.py:49-88` `_compute_knee_eps`, `_fit_dbscan_at_knee` |
| Agglomerative (Ward) | comparison only | `model_comparison.py:172-196` |
| Gaussian Mixture | comparison only | `model_comparison.py:199-223` |
| Ranking | mean rank over Silhouette, Davies–Bouldin, Calinski–Harabasz | `model_comparison.py:226-266` |
| Exploratory (not in app) | shape-normalised + PCA comparison; clustering after removing anomalies | `notebooks/06` cells 1–3, 16–19 |

### 2.2 Choosing k (verified by recomputation, identical to `models/clustering_metrics.json`)

| k | Silhouette | Davies–Bouldin | Calinski–Harabasz | Smallest cluster |
|---|---|---|---|---|
| **2** | **0.4729** | **0.8373** | **1,367.33** | 581 |
| 3 | 0.3839 | 1.0281 | 1,095.25 | 433 |
| 4 | 0.2770 | 1.3785 | 807.33 | 336 |
| 5 | 0.3095 | 1.7812 | 650.98 | 249 |
| 6 | 0.3371 | 2.1552 | 566.75 | 1 |
| 7 | 0.1705 | 2.3790 | 503.33 | 35 |
| 8 | 0.2520 | 2.0107 | 448.17 | 1 |
| 9 | 0.1933 | 2.0667 | 398.33 | 1 |
| 10 | 0.2537 | 1.8219 | 363.62 | 1 |
| 11 | 0.2234 | 1.8350 | 336.17 | 1 |
| 12 | 0.1614 | 1.9742 | 309.79 | 1 |

- **Chosen: k = 2.** The code selects on silhouette only, but **all three indices agree on k = 2**. This is a stronger argument than the code makes, and it isn't written anywhere.
- From k = 6 upwards, K-Means creates single-day clusters (the injected anomaly days).
- Saved model: 2 clusters, sizes **1,396 / 581**; `kmeans_cluster` in `clustering_results.csv` equals `kmeans_model.pkl.predict()` for every day.

### 2.3 DBSCAN

| Item | Value |
|---|---|
| min_samples | 8, hard-coded (`clustering.py:97`, `model_comparison.py:128`) |
| eps | **4.4183**, the "knee" of the sorted 8th-nearest-neighbour distance curve (max perpendicular distance to the chord, axes normalised to [0,1]); knee at the 96.81st percentile |
| Result | **1 cluster of 1,917 days + 60 noise points**; silhouette undefined; status "degenerate - single cluster" |
| **New** | The 60 noise days are **exactly** the 60 injected anomaly days (overlap 60/60) |
| Sweep evidence | `thesis_evidence/tables/T05_dbscan_eps_minsamples_sweep.csv`. min_samples ∈ {4, 8, 16} × eps percentiles: small eps → 4–11 clusters but 34–84% noise; eps ≥ about the 90th percentile → 1 cluster. The module comment (`clustering.py:14-31`) explains this and why the earlier eps loop was removed |

### 2.4 Comparison metrics (saved cache `models/model_comparison_cache.json`, computed 2026-09-01, all at k = 2)

| Model | Silhouette ↑ | Davies–Bouldin ↓ | Calinski–Harabasz ↑ | Mean rank | Result |
|---|---|---|---|---|---|
| **K-Means** | 0.4729 (2nd) | 0.8373 (2nd) | 1,367.33 (1st) | **1.667** | **Best** |
| Agglomerative (Ward) | 0.4536 (3rd) | 0.7929 (1st) | 1,324.10 (2nd) | 2.000 | Alternative |
| Gaussian Mixture | 0.6558 (1st) | 2.9566 (3rd) | 58.46 (3rd) | 2.333 | Alternative |
| DBSCAN | N/A | N/A | N/A | — | Not applicable (1 cluster, 60 noise) |

**New explanation of these numbers (recomputed):**
- **Ward agrees with K-Means:** ARI 0.957, sizes 1,417 / 560. It finds the same weekday/weekend split.
- **GMM's high silhouette is misleading:** GMM (k=2) splits **1,940 vs 37** days, and 36 of the 37 are injected anomalies. It separates anomalies, not behaviour types (ARI vs K-Means 0.053). That is why it wins on silhouette but loses badly on DB and CH. The code's mean-rank rule correctly rejects it, but the *reason* isn't stated anywhere.
- **The comparison fixes k = 2 for every method** (`pipeline_controller.py:156`, `model_comparison.py:355`). Ward and GMM are never given their own k or covariance search.

### 2.5 What the clusters mean (recomputed; also `thesis_evidence/tables/T06`)

| Cluster | Days | Weekend share | Injected anomalies | Mean demand | Mean daily peak | Mean-profile peak / trough |
|---|---|---|---|---|---|---|
| **0 = weekdays** | 1,396 | 0.0% | 24 | 1,839.9 kW | 2,723.4 kW | 19:30 / 02:00 |
| **1 = weekends** | 581 | 97.1% (564 weekend + 17 weekday anomaly days) | 36 | 1,510.9 kW | 2,275.3 kW | 19:30 / 01:15 |

- K-Means vs the weekend flag: **ARI 0.9648**; **1.000 when the 60 injected days are excluded**. The 17 "weekday" members of cluster 1 are all injected low-reading anomaly days.
- Both clusters have the same evening-peak shape (19:30). They differ in **level** (weekends are about 18% lower, exactly the generator's 0.82 factor). No seasonal split appears at k = 2, because the ±8% seasonality is smaller than the weekday/weekend gap.
- **On the dashboard, clusters are shown only as a number** in the selected-day panel (`App.jsx:405-410`). Nowhere in the UI, README or reports does it say "cluster 0 = weekdays, cluster 1 = weekends".

### 2.6 How clustering is used downstream: **it does not affect the labels**

- `kmeans_cluster` and `dbscan_cluster` are merged into `anomaly_results.csv` (`anomaly_detection.py:112-114`) and carried into later files. **No rule in `peak_detection.py` or `behavior_labeling.py` reads them.**
- Labels come only from: the Isolation Forest flag, peak percentiles / z-score, and the 25th-percentile mean-demand threshold.
- So clustering is **descriptive**: it shows the two regular demand regimes, which the low-demand rule then rediscovers. All 396 "Holiday / Low" days are weekends (§4.2).
- **For the viva:** say this explicitly. Clustering *validates* the structure (two regimes = weekday/weekend), DBSCAN's noise *cross-validates* the anomaly detector (same 60 days), and labels are rule-based for interpretability. Alternatively, plan to use the cluster as a rule input (future work).

---

## 3. Anomaly detection

### 3.1 Methods, parameters, results

| Method | Where | Parameters | Flagged |
|---|---|---|---|
| **Isolation Forest** (production) | `anomaly_detection.py:30-48`, called `:92-94` | `n_estimators=300`, `contamination=0.03`, `random_state=42`, on the 96 scaled slots | **60 (3.03%)** |
| Z-score (diagnostic only) | `anomaly_detection.py:51-59` | \|z\| ≥ 3.0 on peak_demand or mean_demand | **0** (max \|z\| peak 2.501, mean 2.932) |
| LOF (comparison) | `anomaly_comparison.py:193-220` | `n_neighbors=20`, `contamination=0.03` | 60 |
| One-Class SVM (comparison) | `anomaly_comparison.py:160-190` | `kernel='rbf'`, `nu=0.03`, `gamma='scale'` | 75 |

- `final_is_anomaly` = Isolation Forest only (`anomaly_detection.py:98`). The reason is given in the comment at lines 9–16: the z-score never fires.
- `test_zscore_thresholds.py` output: \|z\| ≥ 3.0 → 0 days; ≥ 2.5 → 2; ≥ 2.0 → 76.

### 3.2 Bootstrap stability comparison (`anomaly_comparison.py:236-294`, cache from 2026-09-01)

**Method:** 20 resamples (seeds 0–19) of 80% of days without replacement. Each detector is refitted, and its flagged set is compared with the full-data flagged set by Jaccard and symmetric difference. Detectors are ranked by mean Jaccard; z-score is excluded because it flags 0 days.

| Model | Flagged | Mean Jaccard | Std | Mean sym. diff. | Rank |
|---|---|---|---|---|---|
| Isolation Forest | 60 | 0.7769 | 0.032 | 13.6 | 1 |
| LOF | 60 | 0.7769 | 0.032 | 13.6 | 2 |
| One-Class SVM | 75 | 0.2812 | 0.0516 | 77.9 | 3 |
| Z-score | 0 | — | — | — | N/A |

Spearman of continuous scores:
- IF–z 0.903 (IF ranks mostly by magnitude)
- IF–LOF 0.205
- IF–OCSVM 0.077
- LOF–OCSVM 0.531

**Caveats found:**
- **Isolation Forest and LOF flag the identical 60 days.** Their tie is broken only by list order (`anomaly_comparison.py:473`, a stable sort).
- **The Jaccard metric has a ceiling of about 0.80.** An 80% subsample can contain at most about 80% of the 60 full-data days, so 0.7769 is close to the maximum possible. This isn't explained on the page.

### 3.3 New: accuracy against the injected ground truth

| Detector | Flagged | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| **Isolation Forest (saved model / production flags)** | 60 | 60 | 0 | 0 | **1.00** | **1.00** | **1.00** |
| LOF (n=20, c=0.03) | 60 | 60 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| One-Class SVM (nu=0.03) | 75 | 30 | 45 | 30 | 0.40 | 0.50 | 0.44 |
| Z-score 3.0 | 0 | 0 | 0 | 60 | — | 0.00 | 0.00 |
| DBSCAN noise (eps 4.4183) | 60 | 60 | 0 | 0 | 1.00 | 1.00 | 1.00 |

Isolation Forest score as a ranking: **ROC-AUC 1.0, average precision 1.0**. A one-feature rule on daily standard deviation also gets ROC-AUC 1.0, because the injected days are very jagged, so this task is easy.

**Contamination sweep** (what tuning would show):

| contamination | 0.01 | 0.02 | **0.03** | 0.04 | 0.05 |
|---|---|---|---|---|---|
| Flagged | 20 | 40 | **60** | 80 | 99 |
| Precision / Recall | 1.00 / 0.33 | 1.00 / 0.67 | **1.00 / 1.00** | 0.75 / 1.00 | 0.61 / 1.00 |
| F1 | 0.50 | 0.80 | **1.00** | 0.86 | 0.75 |

⚠ **Circularity:** 0.03 is exactly the injected rate (60 / 1,977 = 3.03%). No code, notebook or doc justifies 0.03 (§5). Present it as "the true rate is known for this synthetic data; on real data the rate must be estimated".

### 3.4 Agreement and downstream

- IF = LOF = DBSCAN-noise = the injected set (60 days).
- Of the 60 anomaly days: **21 are labelled "Abnormal Demand Day" and 39 "Peak Demand Day"**, because the priority rule puts anomaly + peak under Peak (§4). The dashboard KPI "Abnormal days 21" therefore understates the 60 detected anomalies.
- Preprocessing interaction: the 3×IQR rule removed 691 high readings on 267 days, **56 of which are injected anomaly days** (their ×1.45 readings were clipped and interpolated). Detection still found all 60.

---

## 4. Rules, labels, risk and future prediction

### 4.1 Peak rule (`peak_detection.py:37-44`)

`is_peak = peak ≥ p90 (2,884.67 kW) OR peak_zscore > 2.0 OR (final_is_anomaly AND peak ≥ p75 (2,819.01 kW))`

| Condition | Days |
|---|---|
| peak ≥ p90 | 198 |
| peak_zscore > 2.0 | 69 |
| anomaly AND peak ≥ p75 | 39 |
| **is_peak total** | **281** |

🐞 **Bug:** `peak_zscore` is the **absolute** z-score (`anomaly_detection.py:56`). **All 69 days caught by the z-rule have *negative* z**: they are the days with the **lowest** daily peaks. All 69 are labelled Peak *only* because of this rule. So 69 of the 281 "Peak Demand Days" (25%) are actually the lowest-peak days. Fix (not applied): use the signed z (`z > 2`) or drop the rule.

### 4.2 Labels and risk (`behavior_labeling.py:24-61`)

Priority, first match wins:
1. **Abnormal** (High): anomaly AND not peak
2. **Peak** (Medium): is_peak
3. **Holiday / Low** (Low): mean_demand < p25 = 1,616.61 kW
4. **Normal Weekday** (Normal): everything else

| Label | Days | % | Weekday | Weekend | Injected anomalies |
|---|---|---|---|---|---|
| Normal Weekday Demand | 1,279 | 64.69 | 1,199 | **80** | 0 |
| Holiday / Low Demand Day | 396 | 20.03 | 0 | 396 | 0 |
| Peak Demand Day | 281 | 14.21 | 203 | 78 | 39 |
| Abnormal Demand Day | 21 | 1.06 | 11 | 10 | 21 |

Risk counts are the same as the labels (Normal 1,279 · Low 396 · Medium 281 · High 21).

Validation against the generator:
- **Holiday / Low:** 100% of these days are weekends (there are no holidays in the data), but they cover only **70.2%** of weekends.
- **"Normal Weekday Demand" is given to 80 weekend days**, so the name is wrong for them.
- **Abnormal:** 21/21 are injected anomalies (precision 1.0); the other 39 anomalies are under Peak.
- **Peak months follow the generator's seasonality:** May 55, June 46, July 44 (peak season), vs Oct 3, Mar 5. That part is sensible.

Stale file: `models/behavior_label_summary.json` (Aug 25, written by `train_models.py`) says Holiday/Low 465, Peak 212. **The current CSV says 396 and 281.** The API reads the CSV, so the dashboard is correct; do not quote the JSON.

### 4.3 Future prediction (`behavior_prediction.py:20-87`)

- **Logic:** match historical days with the same month **and** weekday → if none, same month → if none, all history. Predict the most common label. "Confidence" = that label's share of the matched days (lines 62–63). This is a frequency, not a calibrated probability: 2026-10-20 returns "Normal Weekday Demand, 100%".
- **Evaluation in the code: none.**
- **Back-test** (recomputed; identical to the thesis evidence): train before 2024-06-01 (1,613 days), test on 364 later days.
  - Accuracy **78.85%** vs majority baseline **62.36%**.
  - Macro-F1 **0.4764**.
  - It predicted Normal 262, Low 77, Peak 25, and **never "Abnormal"**.

---

## 5. Model selection justification (PP2 comment 2)

| Model / choice | Written justification found | Where |
|---|---|---|
| 96-slot daily profiles as features | **NOT FOUND** (only *what*, not *why*) | `daily_profile.py:4-11` docstring |
| StandardScaler | Generic: "K-Means, DBSCAN, and Isolation Forest perform better when features are standardized" | `reports/model_training_outputs.md:7` (a template file) |
| **K-Means** | Selected by mean rank over 3 indices; "not the top performer on any single metric, but consistently near the top" | `model_comparison.py:20-30`, `:277-282`; saved `explanation` |
| k = 2 | "select optimal k via silhouette score" (method only) | `README.md:285`, `clustering.py:34-46` |
| DBSCAN eps / keep degenerate | Detailed, honest | `clustering.py:14-31`, `:165` |
| Reject GMM despite top silhouette | Stated (worst DB and CH) | `model_comparison.py:20-24` |
| Agglomerative (Ward) | **NOT FOUND** (no reason for including it or for Ward linkage) | — |
| **Isolation Forest** | Selected by bootstrap stability; generic phrase "robust to high-dimensional data" | `anomaly_comparison.py:14-21`, `:317-318` |
| Drop z-score from `final_is_anomaly` | Detailed (max \|z\| 2.50 / 2.93) | `anomaly_detection.py:9-16` |
| Rank detectors by stability, not rate | Detailed | `anomaly_comparison.py:14-21`, `:382-387` |
| LOF, One-Class SVM | **NOT FOUND** (why these two) | — |
| Percentile peak / low thresholds | **NOT FOUND** | — |
| Priority order of labels | **NOT FOUND** (why anomaly + peak → Peak, not Abnormal) | — |
| Frequency-based future prediction | **NOT FOUND** (no alternative considered) | — |
| Replace the dataset | "contains no temporal or cross-variable structure" | `reports/model_comparison.md:15-23` |

---

## 6. Parameters (PP2 comment 3)

| Parameter | Value | Where set | Tuned? | Justification |
|---|---|---|---|---|
| Spike cut | median + 10×IQR (5,190.72 kW) | `preprocessing.py:11-18` | No | NOT FOUND (removes 0 rows) |
| Outlier fence | 3×IQR → [485.49, 2,928.49] kW | `preprocessing.py:28-36` | No | NOT FOUND (removes 691 high readings, incl. on 56 anomaly days) |
| Resample | 15 min, mean, linear interpolation | `preprocessing.py:39-46` | No | Matches data frequency |
| Complete-day rule | all 96 slots | `daily_profile.py:23` | No | Docstring states it |
| Scaler | StandardScaler, defaults | `clustering.py:121` | No | Generic (§5) |
| K-Means k | 2 (searched 2–12) | `clustering.py:34-46, 95-96, 124` | **Yes** (silhouette sweep) | Method stated |
| K-Means n_init / random_state | 20 / 42 | `clustering.py:40, 126` | No | NOT FOUND |
| DBSCAN min_samples | 8 | `clustering.py:97`, `model_comparison.py:128` | No (single value in code; sweep {4, 8, 16} only in thesis evidence) | NOT FOUND in code |
| DBSCAN eps | 4.4183 (knee, 96.81st pct) | `clustering.py:49-77` | **Heuristic** (knee) | Comment `:14-31` |
| Ward / GMM k | 2 (copied) | `model_comparison.py:355`, `pipeline_controller.py:156` | No | NOT FOUND |
| GMM covariance / random_state | 'full' (default) / 42 | `model_comparison.py:201` | No | NOT FOUND |
| IF n_estimators | 300 | `anomaly_detection.py:32`, `anomaly_comparison.py:103` | No | NOT FOUND |
| IF contamination | 0.03 | `anomaly_detection.py:33, 67`; `pipeline_controller.py:168` | No | **NOT FOUND**; equals the injected rate 3.03% |
| IF max_samples / max_features | defaults ('auto' = 256 / 1.0) | — | No | — |
| IF random_state | 42 | `anomaly_detection.py:34` | — | Reproducibility |
| Z-score threshold | 3.0 | `anomaly_detection.py:51, 68` | Probed 3.0/2.5/2.0 | `test_zscore_thresholds.py`; comment `:9-16` |
| LOF n_neighbors / contamination | 20 / 0.03 | `anomaly_comparison.py:196-197` | No | NOT FOUND |
| OCSVM kernel / nu / gamma | rbf / 0.03 / 'scale' | `anomaly_comparison.py:165-169` | No | nu matches contamination (`:14-18`) |
| Bootstrap | 20 resamples × 80%, seeds 0–19 | `anomaly_comparison.py:40-41` | No | Docstring |
| Peak percentiles | p90 and p75 of daily peak | `peak_detection.py:37-38` | No | NOT FOUND |
| Peak z threshold | \|z\| > 2.0 (absolute: bug) | `peak_detection.py:41` | No | NOT FOUND |
| Low-demand threshold | p25 of mean demand (1,616.61 kW) | `behavior_labeling.py:24` | No | NOT FOUND |
| Label priority | Abnormal > Peak > Low > Normal | `behavior_labeling.py:33-57` | No | NOT FOUND |
| Risk mapping | High / Medium / Low / Normal | `behavior_labeling.py:35-52`, `behavior_prediction.py:12-17` | No | NOT FOUND |
| Prediction fallbacks | month+weekday → month → all | `behavior_prediction.py:46-57` | No | NOT FOUND |
| Dashboard "recent abnormal" | last 10 only | `analysis_service.py:53-57` | — | — |

---

## 7. Fine-tuning (PP2 comment 4)

### 7.1 What is done

1. **K-Means k:** silhouette sweep over k = 2…12 (`clustering.py:34-46`).
2. **DBSCAN eps:** k-distance knee (a heuristic, not a search). A one-off eps × min_samples sweep exists only in `thesis_evidence/tables/T05`.
3. **Clustering algorithm:** mean-rank selection over 3 indices.
4. **Anomaly detector:** bootstrap-stability selection.
5. **Z-score threshold:** probed manually (3.0 / 2.5 / 2.0).

### 7.2 What is NOT tuned

Not tuned:
- K-Means `n_init` / `init`
- DBSCAN `min_samples` (in code)
- Ward and GMM k
- GMM covariance type
- **Every Isolation Forest parameter:** `n_estimators`, `contamination`, `max_samples`, `max_features`
- LOF `n_neighbors`
- OCSVM `nu` / `gamma`
- All percentile thresholds and IQR factors

No grid search, Optuna or cross-validation anywhere in the app or notebooks.

### 7.3 What can realistically be tuned before the viva (read-only scripts writing to a separate folder; about 3–5 h in total)

| # | What | How | Expected / measured result |
|---|---|---|---|
| 1 | **K-Means k** (present) | Show all 3 indices per k (§2.2) + an elbow (inertia) plot + stability (ARI across 10 seeds) | k = 2 wins on all three; easy, strong |
| 2 | **DBSCAN eps × min_samples** | Grid over eps percentiles × min_samples {4, 8, 16} with silhouette / noise % (already in T05) | No setting gives ≥ 2 clusters with < 25% noise; the 1-cluster result is the honest optimum |
| 3 | **GMM** | n_components 1–6 × covariance {full, diag, tied, spherical} by **BIC** | Quick check: BIC (diag) falls steadily 1 → 6 and doesn't settle, which supports *not* choosing GMM |
| 4 | **Isolation Forest** | Grid: contamination {0.01–0.05}, n_estimators {100, 200, 300, 500}, max_samples {128, 256, 512, 1.0}. Select **unsupervised** by bootstrap stability; then **validate** against the injected truth | Sweep above: contamination 0.02 → F1 0.80, 0.03 → 1.00, 0.04 → 0.86 |
| 5 | LOF / OCSVM | n_neighbors {10, 20, 35, 50}; nu {0.01–0.05} × gamma {scale, 0.001, 0.01} | Shows why OCSVM lags (precision 0.40 at defaults) |
| 6 | Thresholds | Sensitivity of label counts to p90/p75/p25 ± 5 points | Shows how stable the labels are |

**How to present it honestly:**
- Choose parameters with *unsupervised* criteria (indices, BIC, stability).
- Then *validate* against the generator's truth: 60 injected days, weekday/weekend split.
- Do not claim the truth was unknown when choosing 0.03.

---

## 8. Evidence and outputs

| Artefact | Path | Notes |
|---|---|---|
| Models | `models/kmeans_model.pkl`, `dbscan_model.pkl`, `isolation_forest_model.pkl`, `profile_scaler.pkl` (Sep 1) | Load in `.venv`; K-Means predictions match saved CSV |
| Metrics | `models/clustering_metrics.json` (current) | `anomaly_metrics.json` and `behavior_label_summary.json` are **stale** (Aug 25, from `train_models.py`) |
| Comparison caches | `models/model_comparison_cache.json`, `anomaly_comparison_cache.json` (Sep 1, fresh) | Served by the API |
| Processed data | `data/processed/*.csv` (Sep 1) | `*_OLD` files are the May run on the old dataset |
| Notebooks | `notebooks/06_model_comparison.ipynb` | Generator + exploratory comparison (20 code cells, all executed; cell 13 raised a TypeError, fixed in cell 14, which wrote the dataset) |
| Figures (current, good for slides) | `thesis_evidence/figures/F01–F13` | k selection, algorithm comparison, DBSCAN k-distance, cluster profiles, PCA, bootstrap stability, IF scores, top anomalies, peak thresholds, label mix, weekday vs weekend profile |
| Figures (stale) | `reports/figures/*.png` (Aug 25) | `clustering_comparison.png` shows **old-dataset** numbers; `cluster_profiles.png` shows a k=6 run |
| Tables | `thesis_evidence/tables/T01–T23` | Includes k sweep, DBSCAN sweep, cluster profiles, back-test |
| Tests | None. `test_zscore_thresholds.py` is a print script (ran: 0 / 2 / 76 days at 3.0 / 2.5 / 2.0) | `thesis_evidence/scripts/api_smoke_test.py` exists outside BI |

**Backend endpoints** (smoke-tested against the running instance; GET only):

| Method | Endpoint | Result |
|---|---|---|
| GET | `/health` | 200 |
| GET | `/docs` | 200 |
| GET | `/api/dashboard-summary` | 200, 0.08 s |
| GET | `/api/model-comparison` | 200 (cached) |
| GET | `/api/anomaly-comparison` | 200 (cached) |
| GET | `/api/predict-future-behavior?date=2026-10-20` | 200, Normal, 100% |
| GET | `?date=not-a-date` | **200** with `success:false` |
| GET | `/api/get-day-profile?date=2025-01-25` | 200 |
| GET | `/api/get-day-profile?date=2030-01-01` | **200** with `success:false` |
| GET | `/api/download-report` (all / Abnormal) | 200 CSV (355 KB / 3.7 KB) |
| POST | `/api/generate-daily-profiles`, `/run-clustering`, `/run-anomaly-detection`, `/detect-peak-days`, `/generate-behavior-labels` | **Not called**: they rewrite `data/processed` and `models` |

**Dashboard pages:**
1. **Dashboard** (`App.jsx`):
   - 5 KPI cards
   - label distribution chart
   - risk distribution chart
   - top-15 anomalous days
   - anomaly-score trend (last 180 days)
   - day selector with 96-slot profile + cluster IDs
   - recent abnormal days (last 10) with "LIME →"
   - future prediction panel
   - "Abnormal days only" filter
   - report download
2. **Model Comparison** (`ModelComparison.jsx`): overview, why selected, table, silhouette/DB charts, ranking.
3. **Anomaly Comparison** (`AnomalyComparison.jsx`): overview, table, stability charts, ranking, Spearman.
4. **Other components:** iframes for forecast, XAI, NN.

---

## 9. Gap analysis

### 9.1 Status against the four panel comments

| # | Comment | Status | Evidence | Missing for the viva |
|---|---|---|---|---|
| 1 | Moderate idea about clustering | **Partially done** | `model_comparison.py`, `clustering.py`, cache, T02–T07, F01–F05 | (a) Say **what the clusters are**: 0 = weekdays, 1 = weekends (ARI 0.965 / 1.000). (b) Explain **why GMM's silhouette is high** (it isolates the 37 anomaly-heavy days). (c) Explain that DBSCAN's noise = the injected anomalies. (d) State clearly that **clustering does not drive the labels**, and why. (e) Show cluster meaning on the dashboard or slides. (f) Per-method k/BIC selection instead of k=2 for all |
| 2 | Why models were selected | **Partially done** | Comments in `clustering.py:14-31`, `anomaly_detection.py:9-16`, `model_comparison.py:20-30`, `anomaly_comparison.py:14-21` | Why 96-slot profiles; why K-Means / IF / LOF / OCSVM / Ward were candidates; why rule-based labels; why frequency prediction. **Ground-truth validation (§3.3) is the strongest new argument** |
| 3 | Parameters used, why? | **Mostly not done** | §6 table; most say NOT FOUND | Reasons for contamination 0.03, 300 trees, min_samples 8, n_neighbors 20, p90/p75/p25, 3×IQR / 10×IQR, label priority |
| 4 | Fine-tuning | **Partially done** | k sweep, knee eps, mean-rank, bootstrap | No search for IF / LOF / OCSVM / GMM / thresholds. Run §7.3 items 1, 3, 4 (≈ 3 h) and present selection + validation |

### 9.2 Bugs, misleading results, inconsistencies

1. 🐞 **Peak rule uses \|z\|:** 69 lowest-peak days labelled "Peak" (`peak_detection.py:41` + `anomaly_detection.py:56`).
2. **"Normal Weekday Demand" given to 80 weekend days.** "Holiday / Low" is really "low weekend" (the data has no holidays).
3. **39 of 60 anomaly days labelled Peak.** The "Abnormal days 21" KPI understates the 60 detected anomalies.
4. **IF/LOF tie broken by list order;** the bootstrap Jaccard ceiling (≈0.80) is not explained.
5. **contamination = 0.03 equals the injected rate** with no written reason; a panel member could call it "tuned to the answer".
6. **Stale or wrong docs:**
   - `README.md:56, 168, 231` name the wrong dataset (`load_forecasting_dataset_corrected.csv`).
   - `README.md:256` run command fails.
   - `README.md:286` and the `pipeline_runner.py:22` / `anomaly_detection.py:70` docstrings still say "combine flags with OR".
   - `README.md:25` claims BI "integrates LIME-based explainability"; LIME is in the XAI component, on a different dataset.
7. **Stale outputs:**
   - `models/behavior_label_summary.json` (465/212 vs 396/281)
   - `models/anomaly_metrics.json`
   - `reports/model_comparison.md`, `reports/*.csv`, `reports/figures/*` (old dataset, silhouette 0.011)
   - `reports/model_training_outputs.md` ("X" placeholders)
8. **`train_models.py` has drifted:** k 2–10, eps loop from 1.6 (+0.4), OR anomaly logic, peak rule without the z condition. Running it would overwrite outputs with different results.
9. **Errors return HTTP 200** with `success:false` (controller pattern), not 4xx.
10. **Prediction "confidence"** is a frequency (100% on 2026-10-20), not a calibrated probability; the model never predicts "Abnormal".
11. **Dataset mismatch with XAI:** 2025-01-25 peak 2,766.43 kW in BI vs 1,894.85 kW in XAI. The XAI page states this.
12. **Legacy files:** `App.js`, `index.js`, `FutureBehaviorPrediction.js`, `frontend/build/` (CRA) are unused but could confuse an examiner.
13. **Requirements drift:** `requirements.txt` lists `sqlalchemy` and `jupyter` (not in `.venv`; never imported) and `matplotlib 3.7.1` / `seaborn 0.12.2` (`.venv` has newer versions). `data_loader.py:28` uses the deprecated `infer_datetime_format`.
14. **Hard-coded values:**
    - `BASE_URL = 'http://127.0.0.1:8001'` (`App.jsx:16`)
    - XAI URL `localhost:5173` (`App.jsx:17`)
    - `http://localhost:3000` CORS (`config.py:13`)
    - Windows paths in `components.config.js`

### 9.3 Live-demo risks

- **Do not press any "run pipeline" (POST) action:** it rewrites outputs and makes the comparison caches recompute (~14 s).
- **Start with `start-all.py`, not the README command.**
- **The XAI "LIME →" link needs the XAI app running** (port 5173).
- **The panel may notice:** 69 low days shown as "Peak"; weekend days called "Normal Weekday".

---

## 10. Final presentation readiness

### 10.1 What can be shown now

**Presentation (10 min):**
1. Problem.
2. Data and how it was generated (honest).
3. Pipeline diagram (§1.4).
4. Clustering: the k sweep, with all 3 indices at k=2 (§2.2, F01); the comparison table with the GMM explanation (§2.4, F02); cluster meaning = weekday/weekend (§2.5, F04, F13).
5. DBSCAN knee (F03).
6. Anomaly comparison + bootstrap (F06) + **ground-truth precision/recall** (§3.3).
7. Labels and risk (F10–F12).
8. Back-test 78.85% vs 62.36%.
9. Integration with XAI.
10. Limitations + tuning plan.

**Demo (10 min):**
1. `start-all.py`
2. Dashboard KPIs and charts
3. Select a day → 96-slot profile + cluster
4. Abnormal-days table → "LIME →" (2025-01-25)
5. Model Comparison page
6. Anomaly Comparison page
7. Future prediction (a weekday vs a Saturday)
8. Download report
9. Swagger `/docs`

### 10.2 Twenty likely viva questions

| # | Question | How the code / evidence answers |
|---|---|---|
| 1 | What are your clusters? | k=2: cluster 0 = 1,396 weekdays, cluster 1 = 564 weekends + 17 anomaly weekdays; ARI vs weekend 0.965 (1.000 without anomalies). Same 19:30 evening peak, weekends about 18% lower |
| 2 | Why k = 2? | Silhouette 0.4729, Davies–Bouldin 0.8373 and Calinski–Harabasz 1,367 are all best at k=2 out of 2–12; k ≥ 6 creates single-day clusters |
| 3 | Why K-Means over GMM, which has a higher silhouette? | GMM splits 1,940 vs 37 (36 anomalies) → high silhouette but worst DB (2.96) and CH (58); mean rank 1.667 vs 2.333 |
| 4 | Ward gives almost the same result: why K-Means? | ARI 0.957; K-Means is faster, predicts new days (`.predict`) and ranks best overall |
| 5 | Why is DBSCAN a single cluster? | Data has one dense region; the eps knee (4.4183, 96.8th pct) gives 1 cluster + 60 noise; smaller eps → 34–84% noise (T05). Noise = the 60 injected anomalies |
| 6 | Does clustering affect the labels? | No: labels use IF + percentile rules. Clustering confirms the weekday/weekend regimes, which the low-demand rule then captures |
| 7 | Why Isolation Forest? | Most stable under 20 bootstraps (Jaccard 0.777, tie with LOF); matches all 60 injected anomalies (P = R = 1.0); fast on 96-dim data |
| 8 | Why contamination 3%? | Honest: it equals the generator's 60 / 1,977 rate. Sweep: 0.02 → F1 0.80, 0.04 → 0.86. On real data, estimate the rate or use a score threshold |
| 9 | Why 300 trees? | Not tuned in code. Plan: n_estimators {100–500} by stability; IF results are stable at this size |
| 10 | Why is the z-score not used? | Max \|z\| is 2.50 (peak) / 2.93 (mean): it never reaches 3.0; the extremes are asymmetric |
| 11 | How did you compare anomaly detectors without labels? | Bootstrap stability (`anomaly_comparison.py`); now also validated against injected truth |
| 12 | How is a peak day defined? | p90 OR \|z\| > 2 OR (anomaly AND p75). **Admit the \|z\| bug** (69 low days) and the fix |
| 13 | Why are anomaly days labelled Peak? | Priority rule: anomaly + peak → Peak (39 days). The Abnormal label (21) = anomalies that are not peaks |
| 14 | How is the future label predicted, and how accurate is it? | Month + weekday frequency with fallbacks. Back-test: 78.85% vs 62.36% baseline, macro-F1 0.48; never predicts Abnormal |
| 15 | What parameters did you tune? | k (silhouette sweep), eps (knee), model choice (mean rank, stability). The rest are fixed; show the tuning plan / results (§7.3) |
| 16 | Is the data real? | No: generated by notebook 06 with a known recipe and 60 injected anomalies. That allows true precision/recall. Real CEB data is future work |
| 17 | Why standardise each slot? | Equal weight per time slot; keeps level differences (weekday vs weekend) visible to K-Means |
| 18 | What does the risk level mean? | A fixed map from label: Abnormal → High, Peak → Medium, Low → Low, Normal → Normal |
| 19 | How does BI connect to the other components? | "LIME →" opens the XAI page with the date; iframes embed the teammates; `start-all.py` runs all four |
| 20 | What would you improve? | Fix the signed z-score; rename labels; tune IF / GMM / thresholds with stability + BIC; use clusters in the rules; real data with holidays; proper HTTP errors |

---

*Method:* `bi_audit_check.py` in the session scratchpad (outputs `bi_audit_check.json`). It regenerates the dataset from notebook 06's code, recomputes clustering, anomaly and label results from the saved files and models, and reruns the thesis back-test. None of these checks wrote to `behaviour-intelligence/` (verified with a marker file).
