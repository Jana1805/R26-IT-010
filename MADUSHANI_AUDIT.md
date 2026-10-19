# Audit — XAI component of IT22273062 (Madushani R.P.)

**Audit date:** 2026-10-18 · **Viva:** 19–21 Oct 2026 · **Scope:** `madushani_xai/` plus its links to `behaviour-intelligence/`, `start-all.py`, `PROJECT_SUMMARY.md`, `THESIS_EVIDENCE_IT22545176.md`.

**Mode:** Read-only. No project file was changed, created or deleted, apart from this report. All checks ran either in-process or on scratch copies under the session scratchpad. The backend was started once on port 8000 for a smoke test and then stopped. Interpreter used: `madushani_xai/venv/Scripts/python.exe` (Python 3.12.7).

PP2 panel comments being addressed:
1. "Lacks idea on the models used"
2. "Need to have a clear idea on the model architecture"
3. "A model comparison needs to be done"

> **The three findings that matter most for the viva (details in §6):**
> 1. **The dataset target is exactly `Load Demand = 100 × Temperature − 1300`.** The maximum residual of a linear fit is 5×10⁻⁷ kW, and the other 11 features have coefficient 0. Every result (LR R² = 1.0, the Temperature SHAP of about 157 kW, the "drift" of the other features) follows from this.
> 2. **Every LIME weight shown in the UI has the wrong sign** (a code bug, proven in §6.2). The UI says high temperature pushes a peak day's demand *down* by about 355 kW. It actually pushes it *up* by about 355 kW.
> 3. **The BI → XAI "Show LIME Explanation" button shows the wrong instance.** None of BI's 60 anomaly days match the 15 saved instances. Every click opens instance #01 (a *low*-demand reading from 2022-11-04) under a banner reading "Anomaly detected on <clicked date>".

---

## 1. Component overview

### 1.1 What it does

| | |
|---|---|
| **Problem** | Demand-forecasting ML models are black boxes. Analysts need to know *which factors drive demand*, *whether that changes over time*, and *why a particular reading was predicted as it was*. |
| **Input** | `behaviour-intelligence/data/raw/load_forecasting_dataset_corrected.csv`: 189,888 rows at 15-minute intervals, 2020-01-01 → 2025-05-31. It has 15 columns: 12 features, `Season` (unused), `Timestamp`, and the target `Load Demand (kW)`. |
| **Model explained** | Its **own** XGBoost regressor (`backend/outputs/xgb_model.pkl`), trained in notebook 1. It does **not** explain the team's neural models (cnn, lstm, transformer, cnn_lstm_b, …), the scenario ensemble, or the behaviour labels. See §1.3. |
| **Output 1: SHAP Temporal Drift** | Mean \|SHAP\| per feature for each year 2020–2025, yearly rankings, 2020→2025 drift, and "insights". File: `temporal_drift.json`. |
| **Output 2: LIME "Anomaly" Diagnosis** | LIME explanations for 15 sampled readings (3 low / 4 medium / 4 high / 4 peak). File: `anomaly_diagnosis.json`. Also an on-demand LIME explanation for any historical date (`/api/explain-date`). |
| **UI** | React dashboard with two pages: `/temporal-drift` and `/anomaly-diagnosis`. |

Naming is inconsistent, and the panel may notice:
- The README calls it "Component 4 — Explainable AI".
- Notebook 1 is titled "Component 1 — SHAP Temporal Drift" and notebook 2 "Component 2 — LIME Anomaly Diagnosis".
- `app.py` comments use "Component 1/2".
- The UI tags read "Component 01 SHAP" and "02".

### 1.2 Folder / file structure

```
madushani_xai/
├── README.md                         Main doc: abstract, model comparison table, ASCII architecture, setup, API, integration
├── .gitignore                        Ignores venv, __pycache__, *.pkl (!), node_modules. Lines 6–10 are UTF-16 garbage (encoding mix-up)
├── generate_anomaly_diagnosis.py     Stand-alone script, same logic as notebook 2. Regenerates anomaly_diagnosis.json (reproduces it exactly, verified)
├── notebooks/
│   ├── 1_shap_temporal_drift.ipynb   EDA → IQR cleaning → chrono split → Optuna (50 trials) → XGBoost → LR/RF comparison → save pkl → per-year SHAP → JSON
│   └── 2_lime_anomaly_diagnosis.ipynb Loads pkl → LIME explainer → 15 stratified instances → JSON
├── backend/
│   ├── app.py                        FastAPI: /, /api/temporal-drift, /api/anomaly-diagnosis, /api/explain-date (live LIME)
│   ├── requirements.txt              Unpinned: fastapi, uvicorn[standard], pandas, numpy, xgboost, shap, scikit-learn, optuna, joblib, lime
│   └── outputs/
│       ├── xgb_model.pkl             Trained XGBRegressor (545 KB)
│       ├── temporal_drift.json       SHAP by year + rankings + drift + model_comparison + model_performance + insights
│       ├── anomaly_diagnosis.json    15 LIME instances + meta (thresholds)
│       └── demand_reduction.json     ORPHAN: no notebook produces it, no endpoint serves it (endpoint removed per README)
├── frontend/                         React 18 + Vite 5 + Recharts + React Router; node_modules installed
│   ├── vite.config.js                Port 5173; proxies /api → http://localhost:8000
│   ├── index.html, package.json
│   └── src/
│       ├── main.jsx, App.jsx         Router; sidebar; "focused" full-width view when ?source=bi
│       ├── App.css, index.css
│       ├── components/               EMPTY
│       └── pages/
│           ├── TemporalDrift.jsx     SHAP page: KPI cards, line chart, ranking cards, drift bar chart, guide
│           ├── LimeAnomalyDiagnosis.jsx LIME page: stats, instance list + filter, contribution bars, R² bar, BI deep-link handling
│           └── *.css
└── venv/                             Python 3.12.7 venv: fastapi 0.141.1, xgboost 3.4.1, shap 0.52.0, lime, sklearn 1.9.0, optuna 4.9.0.
                                      NO jupyter/ipykernel, NO pytest/httpx
```

Not present: tests, figures/PNGs (neither notebook has any plot output), CSV results, a git repository inside `madushani_xai/`, or the `frontend/public/` folder the README lists.

### 1.3 Connections to other components

| Direction | Mechanism | Evidence |
|---|---|---|
| XAI → BI data | Reads BI's raw CSV directly from disk | `backend/app.py:47-51`, `generate_anomaly_diagnosis.py:26-30`, both notebooks (`DATASET_CANDIDATES`) |
| BI → XAI | Opens a new browser tab at `http://localhost:5173/anomaly-diagnosis?source=bi&date=YYYY-MM-DD` | `behaviour-intelligence/frontend/src/App.jsx:17-24`, `FutureBehaviorPrediction.jsx:18,30-31` |
| BI shell → XAI | iframe/link card ("Explainable AI", owner Madushani, `http://localhost:5173`) | `behaviour-intelligence/frontend/src/components.config.js:23-33` |
| XAI → BI | "Back to Dashboard" link, hard-coded `http://localhost:3000` | `LimeAnomalyDiagnosis.jsx:154,230,254` |
| XAI ↔ neural forecasting (cnn, lstm, transformer, cnn_lstm_b, cnn_transformer_b, cnn_lstm_mc, cnn_transformer_mc) | **NOT FOUND.** No code reads those models, their predictions, or their API (port 8003). A grep of `electricity-demand-sri-lanka/` and `final_research/` finds no SHAP or LIME code of their own either. | grep, see §6 |
| XAI ↔ scenario component (`final_research`) | **NOT FOUND.** Only CORS entries mention port 5173. | `final_research/backend/app.py:15` |

**Dataset mismatch:** BI now labels days from `synthetic_realistic_load.csv`, while XAI explains `load_forecasting_dataset_corrected.csv`. So the same date has different demand values in the two apps. This is also disclosed in `PROJECT_SUMMARY.md:44` and `THESIS_EVIDENCE_IT22545176.md:851`.

**Unused interface:** XAI expects `source=bi-predict` together with a matched historical date, and only then calls `/api/explain-date` (`LimeAnomalyDiagnosis.jsx:73,86-101`). BI only ever sends `source=bi`, and BI's backend has no `matched_dates` field (a grep found none). So the live-LIME endpoint is **never reached from BI**.

### 1.4 How to run

| Item | Value |
|---|---|
| One command | `python start-all.py --only xai` from the workspace root. This uses `madushani_xai/venv/Scripts/python.exe` (`start-all.py:63-77`). |
| Backend (manual) | `cd madushani_xai/backend` then `..\venv\Scripts\python.exe -m uvicorn app:app --port 8000` |
| Frontend (manual) | `cd madushani_xai/frontend` then `npm run dev` (Node v22.17.1 is present; deps installed) |
| URLs | Dashboard `http://localhost:5173` · API `http://127.0.0.1:8000` · Swagger `http://127.0.0.1:8000/docs` |
| Config | No config file. Everything is hard-coded: ports, CORS origins (`app.py:21`), dataset path (`app.py:47-51`), proxy (`vite.config.js:7-12`), back-link URL. |
| Startup cost | Imports in about 2.4 s; the startup hook loads the 26 MB CSV and builds LIME in about 2.2 s |
| Smoke test (this audit) | `/` 200 · `/api/temporal-drift` 200 (4 ms) · `/api/anomaly-diagnosis` 200 (5 ms) · `/api/explain-date?date=2023-07-15` 200 (66 ms) · future date `2026-10-20` → 404 · `bad-date` → 422 · CORS for `http://localhost:3000` OK |
| **Do not** | Re-run notebook 1 before the viva. It retrains and **overwrites** `xgb_model.pkl` and `temporal_drift.json`, and the venv has no Jupyter anyway. |

---

## 2. Models used (Panel comment 1)

| # | Model / method | Library | Where (file → function / cell) | Role |
|---|---|---|---|---|
| 1 | **XGBoost regressor** (`XGBRegressor`, `reg:squarederror`) | xgboost 3.x | `notebooks/1_shap_temporal_drift.ipynb` cells 10 (`objective`), 12 (`final_model`); loaded in `backend/app.py:96` (`load_live_explainer`) | The forecasting model being explained |
| 2 | **Optuna TPE** hyperparameter search | optuna | Notebook 1 cell 10 (`objective`, `optuna.create_study(sampler=TPESampler(seed=42))`) | Tunes XGBoost |
| 3 | **Linear Regression** | sklearn | Notebook 1 cell 16 | Comparison baseline only |
| 4 | **Random Forest** (`n_estimators=100, max_depth=15`) | sklearn | Notebook 1 cell 16 | Comparison baseline only |
| 5 | **SHAP TreeExplainer** | shap | Notebook 1 cell 20 (`shap.TreeExplainer(yr_model).shap_values(X_yr)`) | Global importance per year → temporal drift |
| 6 | **6 per-year XGBoost models** (one per year, same best params, each trained on a 2,000-row sample of that year) | xgboost | Notebook 1 cell 20 (`yr_model`) | These are what SHAP actually explains. **Not** the deployed model (see §6.3). |
| 7 | **LIME `LimeTabularExplainer`** (regression mode, default `QuartileDiscretizer`, default kernel width = 0.75·√12 ≈ 2.60, `num_samples=1000`, 2,000-row background, `random_state=42`) | lime | Notebook 2 cells 3, 5; `generate_anomaly_diagnosis.py:85-107`; `backend/app.py:117-123` (`load_live_explainer`), `:180-185` (`explain_date`) | Local per-instance explanation |
| 8 | **IQR outlier filter** on the target (1.5×IQR) | pandas | Notebook 1 cell 6; notebook 2 cell 2; `app.py:102-106`; `generate_anomaly_diagnosis.py:55-61` | Preprocessing (removes 1,281 rows = 0.67%) |
| 9 | **Percentile demand levels** (p25 = 1366.45, p75 = 1634.11, p90 = 1753.72 kW) | pandas | `app.py:71-79` (`_get_demand_level`), notebook 2 cell 4 | Labels instances low / medium / high / peak |

Not used anywhere: Integrated Gradients, attention maps, surrogate trees, permutation importance, PDP/ICE, counterfactuals, or SHAP on neural models. **NOT FOUND.**

### Why each was chosen (written justification found)

| Choice | Justification in the repo | Assessment |
|---|---|---|
| XGBoost | README §"Model Development & Comparison" and notebook 1 cell 15: *"SHAP's TreeExplainer computes exact (not approximate) Shapley values for tree-based models"*. A tree model is "the safer choice if this pipeline is later applied to real, noisier metered demand data". | Present and honest. A panel may reply that SHAP is also exact (closed form) for a linear model. The defensible argument is generality to non-linear real data, not exactness. |
| Optuna / TPE | Notebook 1 cell 9: "Bayesian optimisation (TPE sampler)"; validation is the last 20% of train | Present (method only; no reason given for TPE over grid/random search) |
| SHAP | README: global feature importance, "complementary" to LIME | Present, brief |
| LIME | README: local, model-agnostic, instance-level | Present, brief. **No justification** for LIME parameters (1000 samples, 2000 background, discretizer, kernel width). |
| Per-year retrained models for drift | Notebook 1 cell 19: "A separate XGBoost model is trained per year using the Optuna best hyperparameters" | Method stated, **no justification**. It mixes data drift with model-refit variance (§6.3). |
| IQR target filtering | Notebook 1 cell 5: "Extreme target spikes distort the model's understanding of normal demand patterns" | Present. But it removes the extreme readings *before* an "anomaly diagnosis" step (§6.4). |
| LR & RF as baselines | Notebook 1 cell 15: "Objective 2.2 of the proposal commits to comparing multiple forecasting model families" | Present |
| Demand-level thresholds p25/p75/p90 | UI guide text only (`LimeAnomalyDiagnosis.jsx:446`) | **No justification** |
| "Anomaly" definition | **NOT FOUND.** The 15 instances are random samples per demand bin (`sample(..., random_state=42)`), not detected anomalies. | Gap (§6.4) |

---

## 3. Architecture (Panel comment 2)

### 3.1 End-to-end pipeline (as implemented)

```
load_forecasting_dataset_corrected.csv  (behaviour-intelligence/data/raw, 189,888 rows, 15-min)
        │  sort by Timestamp
        ▼
IQR filter on Load Demand (Q1=1365.22, Q3=1635.07, bounds 960.45–2039.84 kW)  → 188,607 rows
        │
        ├──► Chronological 80/20 split: train 150,885 rows | test 37,722 rows (2024-05-01 08:00 → 2025-05-31 23:45)
        │        └─ inner split of train: 120,708 / 30,177 (val); Optuna fits on a 10,000-row random subsample
        │        ▼
        │    Optuna TPE, 50 trials, objective = val RMSE  → best val RMSE 2.3066 kW
        │        ▼
        │    Final XGBRegressor fit on all 150,885 train rows → test RMSE 2.0248 / MAE 1.0512 / R² 0.9999
        │        ├──► LR + RF comparison on same split → temporal_drift.json["model_comparison"]
        │        └──► joblib.dump → backend/outputs/xgb_model.pkl
        │
        ├──► [Notebook 1, SHAP] for each year 2020–2025: sample 2,000 rows → fit NEW XGBRegressor(best_params)
        │        → TreeExplainer → mean|SHAP| → rankings, drift (2025 − 2020), insights → temporal_drift.json
        │
        └──► [Notebook 2 / generate_anomaly_diagnosis.py, LIME] load xgb_model.pkl → background 2,000 rows
                 → sample 3 low/4 medium/4 high/4 peak → explain_instance(num_samples=1000)
                 → anomaly_diagnosis.json
                       ▼
FastAPI backend (port 8000, app.py)
   GET /api/temporal-drift     → temporal_drift.json  (static)
   GET /api/anomaly-diagnosis  → anomaly_diagnosis.json (static)
   GET /api/explain-date?date= → live LIME on that day's max-demand reading (same explainer setup)
                       ▼
React/Vite frontend (port 5173, /api proxied)
   /temporal-drift     TemporalDrift.jsx
   /anomaly-diagnosis  LimeAnomalyDiagnosis.jsx  (+ ?source=bi | ?source=bi-predict&date=&future_date=)
```

### 3.2 Model architecture: deployed XGBoost (`xgb_model.pkl`, verified by loading it)

| Item | Value | Where set |
|---|---|---|
| Type | Gradient-boosted regression trees (`XGBRegressor`), additive ensemble, squared-error objective | Notebook 1 cell 12 |
| Trees (`n_estimators`) | **467** | Optuna (range 100–500) |
| `max_depth` | **3** (so at most 8 leaves per tree) | Optuna (3–8) |
| `learning_rate` | **0.023100** | Optuna (0.01–0.30, log) |
| `subsample` | **0.92481** | Optuna (0.6–1.0) |
| `colsample_bytree` | **0.89361** | Optuna (0.6–1.0) |
| `min_child_weight` | **1** | Optuna (1–10) |
| `reg_alpha` (L1) | **0.78873** | Optuna (0–1) |
| `reg_lambda` (L2) | **0.46647** | Optuna (0–1) |
| `objective` / loss | `reg:squarederror` (MSE) | XGBoost default |
| Optimiser | Gradient boosting with second-order (Newton) leaf weights. No neural optimiser, epochs or batch size. | n/a |
| `random_state` | 42 | Notebook 1 cells 10, 12 |
| Input shape | **(n, 12)** tabular: one 15-min row → one prediction | Notebook 1 cell 6 |
| Features (order) | Temperature, Humidity, Wind Speed, Rainfall, Solar Irradiance, GDP, Per Capita Energy Use, Electricity Price, Day of Week, Hour of Day, Month, Public Event | `app.py:54-63` |
| Lookback / lags | **None.** Not a sequence model; no lag or rolling features; `Season` column ignored. | n/a |
| Scaling | None (trees do not need it) | n/a |
| Output | `Load Demand (kW)` at the same timestamp | n/a |

Per-year SHAP models: same hyperparameters, each fitted on 2,000 rows of one year (`SAMPLE_SIZE=2000`, `RANDOM_STATE=42`, notebook 1 cell 20).

### 3.3 All hard-coded parameters

| Parameter | Value | Location |
|---|---|---|
| IQR multiplier | 1.5 | NB1 c6, NB2 c2, `app.py:105`, `generate_anomaly_diagnosis.py:59` |
| Train/test split | 0.80 chronological | NB1 c8 |
| Optuna inner val split | 0.80 | NB1 c10 |
| Optuna subsample | 10,000 rows (`OPTUNA_SAMPLE`) | NB1 c10 |
| Optuna trials / seed | 50 / 42 | NB1 c10 |
| SHAP sample per year | 2,000 (`SAMPLE_SIZE`) | NB1 c20 |
| LIME background | 2,000 rows, `random_state=42` | NB2 c3, `app.py:114`, gen `:82` |
| LIME perturbations | `num_samples=1000`; `num_features=12` | NB2 c5, `app.py:184`, gen `:107` |
| LIME discretizer / kernel width | library defaults (quartile; 0.75·√12) | implicit |
| Instance counts | 3/4/4/4, `random_state=42` | NB2 c4, gen `:74-77` |
| Demand thresholds | p25/p75/p90 of cleaned data | `app.py:108-112` |
| Live explain row choice | the day's **max** demand reading | `app.py:171` |
| RF baseline | `n_estimators=100, max_depth=15, n_jobs=-1, random_state=42` | NB1 c16 |
| Ports / CORS | 8000; origins 5173, 3000 | `app.py:21,223`; `vite.config.js:7,10` |
| UI confidence colours | R² ≥ 0.9 green, ≥ 0.75 blue, else orange | `LimeAnomalyDiagnosis.jsx:46` |

### 3.4 Existing diagrams / figures

- `madushani_xai/README.md:72-108`: ASCII system architecture (model → SHAP/LIME → JSON → FastAPI → React). Note it says "12 features"; it does not show preprocessing, Optuna or the per-year models.
- `THESIS_EVIDENCE_IT22545176.md:615-616` (Thanujan's report): a mermaid edge from BI to the XAI app.
- **No model-architecture figure, no pipeline figure, and no SHAP plots (summary/beeswarm/dependence) or LIME plots saved anywhere. NOT FOUND.**

---

## 4. Model comparison (Panel comment 3)

### 4.1 Forecasting-model comparison: EXISTS (notebook 1 cell 16, saved in `temporal_drift.json["model_comparison"]`, also in README:45-49)

Same chronological split; test n = 37,722.

| Model | Test RMSE (kW) | Test MAE (kW) | Test R² | Train time | Tuned? |
|---|---|---|---|---|---|
| Linear Regression | 1.43 × 10⁻⁸ | 7.24 × 10⁻¹⁰ | 1.0000 | 0.02 s | n/a |
| Random Forest | 0.01173 | 0.00557 | 0.99999999634 | 6.67 s | No (fixed 100 trees, depth 15) |
| **XGBoost (Optuna)** | **2.02484** | **1.05116** | **0.99989** | `null` (not recorded) | Yes, but on a 10k subsample |

Other saved XGBoost metrics (`model_performance`): train RMSE 2.0437, train MAE 1.0557, train R² 0.9999, best Optuna val RMSE 2.3066, 50 trials.

This audit recomputed the XGBoost test metrics from the saved pkl: RMSE 2.0248, MAE 1.0512 (matches), **MAPE 0.0733%** (not saved anywhere).

**Why LR is perfect.** A linear fit on the full dataset gives intercept **−1300.000000**, a Temperature coefficient of **+100.000000**, and coefficients of 0.000000 for all 11 other features, with a maximum residual of 5.0 × 10⁻⁷ kW. Pearson r(Temperature, Load) = 1.0000, and |r| ≤ 0.005 for every other feature. The target is a deterministic linear function of temperature. So the comparison shows the dataset is synthetic. It says nothing about the models' merits. XGBoost's 2 kW error is simply the step-function approximation error of 467 depth-3 trees fitting a straight line.

**Weaknesses a panel will see in the comparison:**
- RF is not tuned, while XGBoost is tuned. Optuna also tuned on only 10,000 rows, which probably explains why it chose `max_depth=3`.
- There is one split only: no cross-validation (e.g. rolling-origin), no repeated seeds, no significance test.
- No MAPE in the table; no inference-time comparison.
- No naive or seasonal-naive baseline, and no comparison with the team's neural models on the same data.
- The comparison is **not shown in the UI**: `TemporalDrift.jsx` never reads `model_comparison` or `model_performance` (a grep returns nothing).

### 4.2 XAI-method comparison (SHAP vs LIME, or vs others): **NOT DONE**

| Metric | Status |
|---|---|
| LIME local fidelity (R² of the surrogate, `exp.score`) | **Exists** per instance in `anomaly_diagnosis.json`: min 0.0317, mean 0.4498, max 0.6162. Low/high/peak ≈ 0.56–0.62; **medium ≈ 0.03–0.06**. |
| SHAP fidelity (additivity) | Not reported (it holds by construction for TreeExplainer, but this is not stated) |
| SHAP vs LIME agreement (rank correlation, top-k overlap) | **NOT FOUND** |
| Stability (repeat LIME with different seeds; bootstrap SHAP drift) | **NOT FOUND**. LIME's seed is fixed at 42, so instability is hidden. |
| Runtime | **NOT FOUND** in results. Measured in this audit: live LIME ≈ 0.07 s per instance. |
| Faithfulness checks (deletion/insertion, sanity checks) | **NOT FOUND** |
| Ground truth check | **Possible but not done.** The true effect is known (Temperature +100 kW/°C, others 0), so both methods could be scored against it. |

### 4.3 SHAP temporal-drift results (`temporal_drift.json`)

| Year | Temperature mean\|SHAP\| (kW) | #2 feature (kW) |
|---|---|---|
| 2020 | 159.90 | Wind Speed 0.2238 |
| 2021 | 157.87 | Electricity Price 0.1974 |
| 2022 | 160.42 | Wind Speed 0.2362 |
| 2023 | 153.58 | Wind Speed 0.3011 |
| 2024 | 157.12 | GDP 0.2889 |
| 2025 | 157.21 | Rainfall 0.2032 |

Insights saved: most dominant = Temperature (avg 157.6849); "biggest gainer" = Rainfall +0.1751; "biggest loser" = Temperature −2.6901.

Deployed-model SHAP (this audit, 2,000 test rows): Temperature 154.95; the next is Solar Irradiance at 0.029; Wind Speed 0.002. The #2–#12 rankings in the drift JSON do not match the deployed model's.

**Interpretation:** because the true effect of every non-temperature feature is exactly 0, the 0.0–0.3 kW values and their year-to-year "drift" are model-fitting noise (under 0.2% of Temperature). Temperature's own value ≈ 100 × mean|T − mean T| ≈ 100 × 1.6, so its −2.69 kW "decline" is sampling variation in that year's temperatures, not a change in behaviour.

---

## 5. Evidence and outputs

| Artefact | Path | Showable? |
|---|---|---|
| Trained model | `madushani_xai/backend/outputs/xgb_model.pkl` (545 KB; loads in venv; params in §3.2) | Yes (as a fact) |
| SHAP results | `madushani_xai/backend/outputs/temporal_drift.json` | Yes, via UI |
| LIME results | `madushani_xai/backend/outputs/anomaly_diagnosis.json` | Yes, via UI, **but signs are wrong (§6.2)** |
| Model comparison | `temporal_drift.json["model_comparison"]`, notebook 1 cell 16 output, README:45-49 | Notebook/README only |
| Executed notebooks | `madushani_xai/notebooks/*.ipynb` (all cells have outputs) | Yes. Note the outputs show a macOS path `/Users/shivakumar/Desktop/Dewmini/...` and Python 3.14.6, i.e. they were run on another machine. |
| Orphan output | `backend/outputs/demand_reduction.json` (SHAP "actionability" per feature; nothing produces or serves it) | No |
| Plots / figures | **NOT FOUND** | n/a |
| Logs | **NOT FOUND** | n/a |
| Tests | **NOT FOUND**: no test files; pytest/httpx not installed | n/a |

**Checks run during this audit (all read-only; nothing in the project was written):**

| Check | Result |
|---|---|
| Import `app.py`; run startup hook | OK (2.4 s + 2.2 s); 8 routes registered |
| uvicorn on :8000 + curl all endpoints | All behave as designed (200/200/200/404/422); CORS OK |
| Recompute XGBoost test metrics from pkl | Matches saved RMSE/MAE exactly |
| Re-run `generate_anomaly_diagnosis.py` with output redirected to scratch | **Output identical** to saved `anomaly_diagnosis.json` (full JSON equality) |
| Frontend deps | vite 5.4.21, react 18.3.1, react-router-dom 6.30.3, recharts 2.15.4, axios 1.16.0, lucide-react 1.14.0 installed. Build not run (it would write `dist/`). |

---

## 6. Gap analysis

### 6.1 Status against the three panel comments

| Comment | Status | Evidence | Missing for the final viva |
|---|---|---|---|
| **1. Models used** | **Partially done** | README:21-26, 41-55, 143-166; NB1 cells 9-20; NB2 cells 3-5 | (a) A single slide/table listing **every** model and method with its role (§2 table). (b) A clear statement that the deployed XGBoost and the **6 per-year XGBoost models** are different. (c) LIME configuration (discretizer, kernel, samples, background) and why. (d) The LIME sign bug fixed before LIME results are presented. (e) A clear statement of what is *not* explained (neural models, behaviour labels). |
| **2. Architecture** | **Partially done** | README ASCII diagram (README:72-108); hyperparameters only inside NB1 cell 10 output | (a) A proper pipeline diagram including IQR → split → Optuna → final fit → SHAP per year / LIME → API → UI (§3.1). (b) A model-architecture slide for XGBoost: 467 depth-3 trees, lr 0.0231, L1/L2, MSE loss, 12 inputs, no lookback (§3.2). (c) A LIME mechanism diagram (perturb → predict → kernel-weight → ridge on binarised quartile features). (d) The search-space table. None of these exists as a figure. |
| **3. Model comparison** | **Partially done** | NB1 cell 16; `temporal_drift.json` `model_comparison`; README:45-53 | (a) Not visible in the UI or as a figure. (b) Fair setup: tune RF too or note it is untuned; add MAPE and a naive baseline; rolling-origin CV or at least repeated seeds. (c) Clear explanation that LR R² = 1.0 is because `Load = 100·T − 1300` exactly. (d) **No XAI-method comparison** (SHAP vs LIME fidelity/stability/runtime/agreement), which is arguably what an XAI panel expects. The known ground truth (Temperature only) makes a quick, convincing comparison possible. |

### 6.2 Bugs and live-demo risks (ordered by severity)

1. **LIME weights are sign-inverted everywhere (bug).**
   - All three call sites take `list(exp.local_exp.values())[0]`: `backend/app.py:191`, `generate_anomaly_diagnosis.py:112`, notebook 2 cell 5.
   - In regression mode LIME stores the real weights under key `1` and their negation under key `0` (`venv/Lib/site-packages/lime/lime_tabular.py:461-464`). Verified on the max-demand row: `as_list()` gives `Temperature > 29.29: +359.68`, while the stored value is `−359.68`.
   - Effect: every bar in the UI is flipped. For example, instance #15 (32.30 °C, peak) shows Temperature **−353.38 kW**; instance #01 (24.88 °C, low) shows **+351.07 kW**.
   - The guide text (`LimeAnomalyDiagnosis.jsx:440`) says intercept + contributions ≈ prediction. With the saved data this is off by 87–890 kW (e.g. #15: 1035.6 vs 1925.6).
   - Fix (not applied): use `exp.local_exp[1]` (or `exp.as_map()[1]`), then regenerate with `generate_anomaly_diagnosis.py`, which is deterministic and reproduces the file exactly.
2. **BI deep-link shows an unrelated instance under a misleading banner.**
   - BI sends `?source=bi&date=…` (`behaviour-intelligence/frontend/src/App.jsx:19-24`). XAI only searches the 15 saved timestamps (`LimeAnomalyDiagnosis.jsx:107-112`). 0 of BI's 60 anomaly days (`behaviour-intelligence/data/processed/anomaly_results.csv`, `final_is_anomaly`) match.
   - So the focused view always shows instance #01 (2022-11-04 11:15, *low* demand) while the banner says "Anomaly detected on <date> — here is the LIME explanation" (`:149-151`).
   - Workaround for the demo: open `http://localhost:5173/anomaly-diagnosis?source=bi-predict&date=2023-07-15`. This triggers the real live `/api/explain-date` (tested: 200, 66 ms).
3. **The live-LIME feature is never triggered by BI.** `source=bi-predict` and `matched_dates` do not exist on the BI side (grep). This is a documented integration that does not happen.
4. **Temporal-drift line chart is unreadable by default.** Temperature at about 157 forces the y-axis so the other 11 lines sit flat at 0 (`TemporalDrift.jsx:183-205`). The presenter must toggle Temperature off. The drift bar chart is likewise dominated by Temperature −2.69.
5. **"Temporal drift" findings are noise** (§4.3). Rankings #2–#12 change every year because the true effect is 0. A panel member who asks "is Rainfall really becoming more important?" must get an honest "no".
6. **The LIME confidence bar is always orange "Moderate — treat with caution"**, because all R² < 0.75 (`LimeAnomalyDiagnosis.jsx:46,57-61`). Medium instances fill only 3–6% of the bar. The cause is that LIME binarises Temperature into quartile bins and medium readings sit in the two middle bins. It is visible on screen and the presenter should be ready to explain it.
7. **The "Anomaly Diagnosis" page does not diagnose anomalies.** The instances are random draws per demand bin, and IQR removed the 1,281 most extreme readings beforehand (NB2 cell 2, `app.py:102-106`). Expect "where is the anomaly detector?".
8. **Model comparison not in the UI.** The data is served (`/api/temporal-drift`) but never rendered.
9. **Future dates return 404** from `/api/explain-date` (e.g. 2026-10-20). The UI silently falls back to the static list (`LimeAnomalyDiagnosis.jsx:97-101`).
10. **Hard-coded paths/URLs:**
    - Dataset path relative to `../../behaviour-intelligence/data/raw` (`app.py:47-51`). If it is missing, `/api/explain-date` returns 503 and the other endpoints still work.
    - `http://localhost:3000` back links.
    - CORS list and ports are hard-coded.
    - Notebooks use `os.path.abspath('<name>.ipynb')`, so they depend on the working directory.
11. **Reproducibility:**
    - `requirements.txt` is unpinned.
    - The notebooks were executed on another machine (macOS, Python 3.14.6).
    - The venv lacks Jupyter, so the notebooks cannot be re-run from it.
    - `*.pkl` is git-ignored, so a fresh clone has no model.
    - `.gitignore` lines 6–10 are UTF-16 bytes mixed into a UTF-8 file.
12. **Deprecation:** `@app.on_event("startup")` (`app.py:87`) is deprecated in FastAPI. It still works on 0.141.1 (handler registered and executed).

### 6.3 Unclear or undocumented points a panel is likely to probe

- **Which model does the SHAP page explain?** Six per-year models, each fitted and explained on the same 2,000 rows (in-sample), not `xgb_model.pkl`. This is undocumented in the UI. Year-to-year differences therefore include refit variance; there are no confidence intervals or repeated seeds.
- **The README and docstrings contradict the code:**
  - The README lists `backend/generate_anomaly_diagnosis.py`, but the script is at `madushani_xai/` root.
  - The README's deep-link URL `/lime-anomaly-diagnosis?...` (README:338) is wrong; the actual route is `/anomaly-diagnosis`.
  - The `app.py:135` docstring says "2020–2024"; the data covers 2020–2025.
  - The README says Optuna tuned "n_estimators, learning_rate, max_depth, and regularisation". It also tuned subsample, colsample_bytree and min_child_weight.
  - `frontend/public/` and `src/components/` are listed but empty or missing.
- **Dataset provenance:** `load_forecasting_dataset_corrected.csv` has an exactly linear target. Who generated it? Its provenance is undocumented, and the file differs from BI's current `synthetic_realistic_load.csv`.
- **2025 is partial** (14,496 rows, Jan–May), so the 2025 SHAP covers a different season mix from the other years.
- **The LIME weight unit is shown as "kW per feature value".** In fact the weight is the effect of *being in the instance's quartile bin* (e.g. `Temperature > 29.29`). The UI shows the raw value (`= 32.3`) but not the bin rule.
- **Why XGBoost if LR is perfect?** This is answered in the README, but the exactness argument is weak (LinearSHAP is also exact).
- **Component numbering** (1, 2 or 4) and the authorship of the notebook runs (the Mac path contains "Dewmini").

---

## 7. Final presentation readiness

### 7.1 Can be shown now (10-min presentation)

1. The problem and objectives (README:29-66).
2. The pipeline: redraw §3.1 as a figure; nothing ready-made beyond the README ASCII diagram.
3. The XGBoost architecture and hyperparameter table (§3.2), plus the Optuna search space (NB1 cell 10).
4. The model comparison table (§4.1) **with the honest reading**: Load = 100·T − 1300 makes LR exact. XGBoost is kept for generality to non-linear real data and for TreeSHAP.
5. SHAP result: Temperature dominates every year (153.6–160.4 kW). Present the other features as ≈ 0 (consistent with the ground truth), **not** as "drift".
6. LIME: show it **only after fixing the sign bug**, or show `as_list()` rule labels from a notebook. Mention fidelity R² 0.03–0.62 as a limitation.

### 7.2 Can be shown now (10-min demo)

- Start: `python start-all.py --only xai` (or the manual commands in §1.4). Backend ready in under 5 s.
- `/temporal-drift`: KPI cards, then toggle Temperature off so the other lines become visible, then rankings and the drift chart.
- `/anomaly-diagnosis`: filter by level and pick instances. **Warning:** the bars currently show inverted signs.
- Live LIME: `http://localhost:5173/anomaly-diagnosis?source=bi-predict&date=2023-07-15` (works; signs inverted).
- Swagger: `http://127.0.0.1:8000/docs`.
- **Avoid** the BI dashboard's "XAI" button (risk #2) and future dates (404).

### 7.3 Likely viva questions and how the code answers them

| Question | Answer from the code / evidence |
|---|---|
| Which model do you explain, and why XGBoost? | `xgb_model.pkl`, 467 trees, depth 3. Reasons from README:53: exact TreeSHAP, and robustness on non-linear real data. Be ready for "SHAP is exact for linear models too". |
| Explain XGBoost's architecture. | Sequential additive trees; each fits the gradient/Hessian of the MSE loss; shrinkage 0.0231; L1 0.789 / L2 0.466; row/column subsampling 0.92/0.89; output = sum of 467 tree outputs. §3.2. |
| How were hyperparameters chosen? | Optuna TPE, 50 trials, seed 42, val = last 20% of train, fitted on a 10k subsample; best val RMSE 2.3066 (NB1 c10). |
| Why does Linear Regression get R² = 1? | The target is exactly 100·Temperature − 1300 (verified). The dataset is synthetic; the result validates nothing about real-world accuracy. |
| How did you compare models? | Same chronological 80/20 split; RMSE/MAE/R² (NB1 c16). Admit: single split, RF untuned, no MAPE/CV/significance test. |
| How do you compare SHAP and LIME? | **No code for this.** Only LIME R² exists. A ground-truth comparison is possible because the true attribution is known. |
| What does mean\|SHAP\| = 157 kW mean? | On average Temperature moves the prediction about 157 kW from the base value. This equals 100 kW/°C × mean\|T − T̄\| ≈ 1.6 °C. |
| Is there real temporal drift? | Honest answer: no. The non-temperature values are ≤ 0.3 kW noise around a true 0. The per-year models are refits on 2,000 in-sample rows. |
| Why is LIME R² so low for medium demand? | The quartile discretisation turns Temperature into bins; mid-range readings fall in the two middle bins, where the binary surrogate cannot follow the line (R² 0.03–0.06). |
| Why is Temperature negative for peak days? | **This is the sign bug** (§6.2 #1). It must be fixed or explained before the viva. |
| Where is the anomaly detection? | None in this component. The instances are stratified random samples, and IQR removed extremes first. Detection lives in BI (Isolation Forest). The BI → XAI link does not show the clicked day (§6.2 #2). |
| How does this integrate with the other components? | It reads BI's CSV and receives a browser deep-link from BI. There is no link to the neural or scenario models (§1.3). |
| Did you use time-series validation? | Chronological split, yes (NB1 c7-8); no rolling-origin CV. |
| Are results reproducible? | LIME JSON: yes, exactly (verified). SHAP/model: seeds are fixed, but re-running retrains and overwrites; deps unpinned; notebooks run on another machine. |

---

### Appendix: scratch scripts used (outside the project, not part of the component)

These are in the session scratchpad (`C:\Users\THANUJAN\AppData\Local\Temp\claude\d--Y4S1-Research-Component1-Behaviour-Intelligence\26bea7f9-caac-4759-88f7-a3c2d91bb810\scratchpad\`):
- `probe_api.py`: endpoint functions and model params
- `probe_data.py`: linear-fit check, LIME reconstruction, test metrics, deployed-model SHAP
- `probe_lime.py` and `probe_lime2.py`: sign-bug proof
- `gen_copy.py`: reproduction of the LIME JSON into scratch
