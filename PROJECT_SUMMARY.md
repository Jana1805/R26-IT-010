# Project summary

## Purpose

The **Electricity Demand Intelligence System (EDIS) for Sri Lanka** is a SLIIT final-year research project combining daily demand behaviour analysis, neural load forecasting, what-if scenario analysis, and explainable AI. Four independent FastAPI/React applications are presented through a common dashboard shell. The repository demonstrates research on historical datasets; it does not establish a live national utility monitoring service.

## Folder structure

| Folder / file | Contents and responsibility |
|---|---|
| `behaviour-intelligence/` | Main dashboard and behaviour pipeline. `backend/app/` contains API routes, controllers, services and `ml/` algorithms; `frontend/` contains the dashboard, comparisons, prediction panel and teammate app wrapper; `data/raw/`, `data/processed/`, `models/`, `notebooks/` and `reports/` hold datasets, outputs, artifacts and research. Legacy files and `*_OLD` artifacts are also retained. |
| `electricity-demand-sri-lanka/` | Seven-model neural forecasting service. `api/` contains the model registry, feature engineering, lazy model loading and prediction/comparison routes; `frontend/` provides forecasting dashboards; `Models/<model_id>/{runtime,research,evaluation}/` separates deployment artifacts, notebooks and evaluations. Also includes `data/`, `outputs/final_model_comparison/`, `scripts/`, `tests/` and `docs/`. |
| `final_research/` | Tabular forecasting and scenario analysis. `notebooks/` trains/compares models and generates scenarios; `backend/app.py` serves predictions and custom scenarios using `backend/saved_models/`; `backend/outputs/` stores scenario results; `frontend/` provides the scenario dashboard. |
| `madushani_xai/` | XGBoost explanation service. `notebooks/` computes yearly SHAP analysis and LIME examples; `backend/app.py` serves saved results and on-demand date explanations; `backend/outputs/` stores the XGBoost model and JSON outputs; `frontend/` displays temporal drift and local explanations. |
| `thesis_evidence/` | Behaviour-component evaluation scripts, 13 figures and 23 CSV tables, plus machine-readable evaluation and API test summaries. The scripts evaluate a scratch copy to preserve component artifacts. |
| `THESIS_EVIDENCE_IT22545176.md` | Detailed evidence report, sources, reproducibility findings and known defects, gathered on 2026-10-10. |
| `start-all.py` | Standard-library launcher for all four applications, or a selected subset. |

## Tech stack

- **Backend/data:** Python, FastAPI, Uvicorn, Pydantic, pandas, NumPy, SciPy, scikit-learn, pickle/joblib and CSV/JSON artifacts. The behaviour backend has no active database integration.
- **ML/research:** TensorFlow/Keras for neural forecasts; scikit-learn for clustering, anomaly detection and tabular ensembles; XGBoost, SHAP, LIME and Optuna; Jupyter notebooks and Matplotlib/Seaborn for experiments and figures.
- **Frontend:** JavaScript/JSX, React, Vite and Axios; Recharts for behaviour, neural and XAI charts; Tailwind CSS in scenario analysis and React Router in XAI. Most apps use React 18/Vite 5; neural forecasting uses React 19/Vite 8.
- **Environments:** Dependency requirements differ across components. The launcher uses separate virtual environments for XAI, scenario analysis and neural forecasting, and its invoking Python for behaviour analysis.

## Main models and methods

1. **Behaviour intelligence:** Cleans/resamples demand to 15-minute intervals, creates 96-slot daily profiles and standardizes them. K-Means selects `k` from 2–12 by silhouette; DBSCAN uses a nearest-neighbour distance knee. Comparisons include Ward agglomerative clustering and Gaussian mixtures. Isolation Forest (300 trees, 3% contamination) supplies the production anomaly flag; absolute z-scores are diagnostic. Anomaly comparisons include LOF and One-Class SVM with subsampling stability. Percentile/z-score peak rules and ordered rules assign **Abnormal**, **Peak**, **Holiday / Low**, or **Normal Weekday** labels and risk levels. Future labels use historical month/day-of-week frequencies with broader fallbacks. The labels come from rules, rather than direct cluster-to-label mapping.
2. **Neural forecasting:** Serves `cnn`, `lstm`, `transformer`, `cnn_lstm_b`, `cnn_transformer_b`, `cnn_lstm_mc` and `cnn_transformer_mc`. Each uses a **96-step lookback, 20 features and one-step output**. Features combine weather, cyclic calendar encodings, public/Poya events, load lags and rolling statistics. Models and their scalers load on demand and remain cached; runtime does not retrain them. MC Dropout variants provide sampled predictions and configured calibrated uncertainty bounds. The configured default is `cnn_lstm_b`.
3. **Scenario analysis:** Uses 12 weather, economic and temporal features. It compares Linear Regression, Random Forest and Gradient Boosting, then stacks them using five-fold out-of-fold predictions and an Optuna-tuned Ridge meta-learner (50 trials; `alpha=0.001`). The deployed artifact is a `StackingRegressor`. Scenarios alter temperature, electricity price or GDP, compare baseline/modified demand, and report risk and recommendations.
4. **XAI:** A separate tuned XGBoost regressor uses 12 features. SHAP summarizes feature importance by year (2020–2025); LIME explains 15 saved instances and historical dates on demand. A date explanation uses that day's peak retained reading. These explain XGBoost predictions, rather than the behaviour classifier or neural models directly.

## How the components connect

`start-all.py` launches the following local services:

| Component | Backend port | Frontend port |
|---|---:|---:|
| Behaviour intelligence | 8001 | 3000 |
| Neural forecasting | 8003 | 5176 |
| Scenario analysis | 8002 | 5175 |
| XAI | 8000 | 5173 |

Each frontend calls its own REST API. The behaviour dashboard embeds teammate frontends through iframes configured in `frontend/src/components.config.js`, and links to XAI with `?source=bi&date=YYYY-MM-DD`; XAI calls `/api/explain-date` for that date. Integration is primarily through the UI and historical data, with separate models and artifacts. Behaviour currently reads `synthetic_realistic_load.csv`; XAI reads the earlier `load_forecasting_dataset_corrected.csv`, scenario training uses its notebook copy, and neural forecasting reads `electricity_demand_srilanka_fixed.csv`. Consequently, the same date can refer to different demand values across components.

## Key saved results and limits

| Area | Results |
|---|---|
| Behaviour clustering | **1,977 complete days**, 2020-01-01 to 2025-05-30. K-Means selected **k=2**, silhouette **0.4729**, Davies–Bouldin **0.8373**, cluster sizes **1,396 / 581**, broadly separating weekdays/weekends. DBSCAN produced one cluster plus 60 noise days. |
| Behaviour labels/anomalies | Current processed CSV: **1,279 normal (64.69%)**, **396 low (20.03%)**, **281 peak (14.21%)**, **21 abnormal (1.06%)**. Isolation Forest flags **60 days (3.03%)**; 39 also receive peak labels. LOF flags the same 60 days and ties its stability score. |
| Behaviour prediction/testing | Saved temporal holdout: **78.85% accuracy** versus **62.36%** majority baseline, macro-F1 **0.4764** across 364 days. Peak recall is **0.1404** and abnormal recall **0**. Evidence records exact reproduction of saved pipeline outputs and **24/24 API checks passed**. |
| Neural forecasting | On **18,817 aligned saved test predictions**, CNN-Transformer MC ranks first: **MAE 20.4573 kW**, **RMSE 29.2288 kW**, **MAPE 0.9674%**, **R² 0.9745**. CNN-LSTM baseline is close (MAE **20.5186 kW**); their paired comparison gives **p=0.9041**, so the small lead is not statistically convincing. CNN-LSTM MC has no saved prediction CSV and is excluded from ranking. |
| Scenario forecasting | Saved deployed ensemble test **MAE 0.000178 kW**, **RMSE 0.000474 kW**, **R² ≈ 1** on 37,978 test samples. About **99.92%** of meta-learner weight goes to Linear Regression. Saved heat-wave/cold-spell scenarios change demand by **+52.95% / −66.18%**; price/GDP scenarios have essentially zero effect. |
| XAI | Saved XGBoost test **MAE 1.0512 kW**, **RMSE 2.0248 kW**, **R² 0.9999**. Temperature dominates yearly SHAP importance. LIME local-fit R² spans **0.0317–0.6162**, so explanation fidelity varies substantially. |

Interpretation requires care: the behaviour dataset is synthetic with undocumented provenance; no ground-truth anomaly labels establish detection precision/recall. Its absolute-z-score peak rule incorrectly labels **69 low-peak weekend days as peak days**, and IQR cleaning removes 691 high readings before detection. The saved label-summary JSON and older reports contain different counts; the table above follows the current processed CSV and thesis evaluation. Scenario/XAI near-perfect scores reflect an almost linear temperature-demand relationship in their datasets, rather than demonstrated real-grid generalization. The deployed scenario ensemble can extrapolate beyond observed demand ranges. These issues are documented findings, not changes made by this review.

Sources: implementation/configuration files, component READMEs, `THESIS_EVIDENCE_IT22545176.md`, `thesis_evidence/tables/eval_summary.json`, neural comparison CSVs, scenario model metadata/results, and XAI output JSON. Results above are existing saved evaluations; training and application tests were not rerun for this summary.
