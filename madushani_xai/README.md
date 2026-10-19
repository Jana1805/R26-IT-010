# AI-Based Electricity Demand Intelligence — Explainable AI (XAI) System

> **Component 4 — Explainable AI (XAI) Module**
> Final Year Research Project | Sri Lanka Institute of Information Technology (SLIIT)

---

## Research Information

| | |
|---|---|
| **Student Name** | Madushani R.P |
| **Student ID** | IT22273062 |
| **Institution** | Sri Lanka Institute of Information Technology (SLIIT) |
| **Supervisor** | Dr. Nathali Silva |
| **Research Component** | Component 4 — Explainable AI (XAI) for Electricity Demand Intelligence |
| **Academic Year** | 2025 / 2026 |

---

## Abstract

This research component develops an Explainable AI (XAI) system for electricity demand intelligence, providing interpretable justifications for an XGBoost-based demand forecasting model. The system applies two complementary explainability techniques — SHAP (SHapley Additive exPlanations) for global temporal feature importance analysis and LIME (Local Interpretable Model-agnostic Explanations) for local instance-level diagnosis — and presents both through an interactive React dashboard.

The XAI system enables energy analysts and decision-makers to understand not only what the AI model predicts, but why, by revealing which features (temperature, economic factors, temporal patterns) drive demand at a global scale over time and at the level of individual anomalous demand events.

---

## Research Problem & Motivation

Machine learning models for electricity demand forecasting often function as black boxes, producing accurate predictions without justifying their reasoning. This lack of transparency reduces trust and limits adoption in high-stakes energy management decisions. Stakeholders need to understand:

- Which factors most influence electricity demand — and how that influence shifts over time
- Why a specific day is classified as anomalous or showing unusual demand behaviour
- Whether the model's reasoning aligns with domain knowledge before trusting its predictions

This component addresses these gaps by integrating SHAP for temporal drift analysis across six years of data (2020–2025) and LIME for per-instance local explanations across 15 representative demand instances spanning low, medium, high, and peak demand levels.

---

## Model Development & Comparison

Before being adopted as the model this component explains, XGBoost was compared against two other model families on the identical chronological train/test split (188,607 rows, 2020–2025):

| Model | Test RMSE (kW) | Test MAE (kW) | Test R² |
|---|---|---|---|
| Linear Regression | ~0.00 | ~0.00 | 1.0000 |
| Random Forest | 0.0117 | 0.0056 | 0.99999 |
| **XGBoost (Optuna-tuned)** | 2.0248 | 1.0512 | 0.99989 |

**Honest reading of this result:** Linear Regression achieves an essentially perfect fit on this dataset, and both Linear Regression and Random Forest score marginally better than XGBoost on raw error. This indicates the demand values in this dataset are close to a linear function of the inputs, with limited genuine nonlinear structure for a tree ensemble to exploit.

**XGBoost is still the model this component explains — not because it is the most accurate here, but because SHAP's `TreeExplainer` computes exact (not approximate) Shapley values for tree-based models.** That exactness is what the explainability objective actually depends on, and a tree-based model remains the safer choice if this pipeline is later applied to real, noisier metered demand data instead of this dataset. Linear Regression's own explanation is just its coefficients — it wouldn't demonstrate the SHAP/LIME research contribution this component is about.

XGBoost itself was tuned with Optuna (50 trials, TPE sampler) over `n_estimators`, `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`, `min_child_weight`, `reg_alpha` and `reg_lambda`, using a chronological 80/20 split (never random — this is time-series data, so a random split would leak future information into training).

---

## Research Objectives

1. Apply SHAP to quantify global feature importance for the XGBoost demand forecasting model across yearly time windows (2020–2025)
2. Detect temporal drift by tracking how feature importances shift year-on-year
3. Apply LIME to generate local, instance-specific explanations for individual demand predictions
4. Categorise LIME explanations across four demand levels: Low, Medium, High, and Peak
5. Deploy both analyses through a REST API and an interactive two-panel dashboard
6. Enable integration with external components via URL parameters (e.g. from Behaviour Intelligence dashboard)

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│           TRAINED XGBOOST MODEL                     │
│           outputs/xgb_model.pkl                     │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────────────┐
│  SHAP ANALYSIS   │   │       LIME ANALYSIS           │
│  (Notebook 1)    │   │       (Notebook 2)            │
│                  │   │                               │
│  Yearly windows  │   │  15 instances:                │
│  2020 – 2025     │   │  3 Low / 4 Medium /           │
│  12 features     │   │  4 High / 4 Peak              │
│  Drift tracking  │   │  Feature contributions        │
└────────┬─────────┘   └──────────────┬────────────────┘
         │                            │
         ▼                            ▼
  temporal_drift.json      anomaly_diagnosis.json
                                                  
┌─────────────────────────────────────────────────────┐
│           FASTAPI BACKEND  (Port 8000)              │
│                                                     │
│  /api/temporal-drift      │  SHAP yearly data       │
│  /api/anomaly-diagnosis   │  LIME instance data     │
└───────────────────────────┬─────────────────────────┘
                            │
                       JSON Responses
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│           REACT FRONTEND  (Port 5173)               │
│                                                     │
│  01 — SHAP Temporal Drift  │  Feature trends chart  │
│  02 — LIME Anomaly Diag.   │  Instance explainer    │
└─────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend

| Technology | Role |
|---|---|
| Python 3.9+ | Core language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| XGBoost | Primary forecasting model (pre-trained) |
| SHAP | Global feature importance & temporal drift analysis |
| LIME | Local instance-level explanation generation |
| scikit-learn | Preprocessing and supporting ML operations |
| pandas | Data processing |
| numpy | Numerical computation |
| joblib | Model loading |
| Optuna | Hyperparameter optimisation (model training) |

### Frontend

| Technology | Version | Role |
|---|---|---|
| React | 18.2.0 | UI component framework |
| Vite | 5.1.0 | Build tool and dev server |
| React Router DOM | 6.22.0 | Page navigation |
| Recharts | 2.12.0 | Interactive charts (line, bar) |
| Axios | 1.6.7 | HTTP client for API calls |
| Lucide React | 1.14.0 | Icon library |

---

## XAI Methods

### SHAP — Global Temporal Drift Analysis

SHAP (SHapley Additive exPlanations) quantifies how much each input feature contributes to model output across the entire dataset. In this system, SHAP values are computed per year (2020–2025) to track how feature importance evolves over time.

| Analysis | Description |
|---|---|
| **Yearly feature importance** | Mean absolute SHAP values per feature per year |
| **Temporal drift** | Year-on-year change in feature rankings |
| **Feature trends** | Rising vs. declining feature influence over 6 years |
| **Yearly rankings** | Top 5 demand drivers identified per year |

### LIME — Local Anomaly Diagnosis

LIME (Local Interpretable Model-agnostic Explanations) fits a simple linear model around a specific prediction instance to explain why the model made a particular prediction for that individual input.

| Analysis | Description |
|---|---|
| **15 instances** | 3 Low, 4 Medium, 4 High, 4 Peak demand instances |
| **Feature contributions** | Signed weights showing positive/negative impact per feature |
| **Local fit R²** | Confidence score of the local linear approximation |
| **Intercept** | Baseline demand before feature contributions |
| **Actual vs Predicted** | Side-by-side comparison with error |

---

## Project Structure

```
madushani_xai/
│
├── generate_anomaly_diagnosis.py       # Script to regenerate the LIME explanations (same logic as notebook 2)
├── experiments/
│   ├── model_and_xai_comparison.py     # v2 evidence: model comparison, SHAP vs LIME, drift with CIs
│   └── dataset_check.py                # Cross-dataset check behind DATASET_CHECK.md (read-only on data)
│
├── backend/
│   ├── app.py                          # FastAPI application (3 data endpoints, incl. live LIME)
│   ├── requirements.txt                # Python dependencies (pinned)
│   └── outputs/
│       ├── xgb_model.pkl               # Trained XGBoost model
│       ├── anomaly_diagnosis.json      # LIME explanations (15 instances)
│       ├── temporal_drift.json         # SHAP yearly drift data + model comparison
│       ├── v2/                         # JSON from experiments/model_and_xai_comparison.py
│       └── figures/                    # PNG figures served at /api/figures/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                     # Root component with sidebar navigation
│   │   ├── App.css                     # App-level styles
│   │   ├── main.jsx                    # Vite entry point
│   │   ├── index.css                   # Global styles
│   │   └── pages/
│   │       ├── TemporalDrift.jsx       # SHAP temporal drift dashboard
│   │       ├── TemporalDrift.css       # Temporal drift styles
│   │       ├── LimeAnomalyDiagnosis.jsx # LIME anomaly diagnosis dashboard
│   │       ├── LimeAnomalyDiagnosis.css # LIME page styles
│   │       ├── ModelXaiComparison.jsx  # Model & XAI comparison page (v2 evidence)
│   │       └── ModelXaiComparison.css  # Comparison page styles
│   ├── package.json
│   ├── vite.config.js                  # Vite config (proxy: /api → port 8000)
│   └── index.html
│
├── notebooks/
│   ├── 1_shap_temporal_drift.ipynb     # SHAP analysis across 2020–2025
│   └── 2_lime_anomaly_diagnosis.ipynb  # LIME explanations for 15 instances
│
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- npm 9 or higher

---

### 1. Clone the Repository

```bash
git clone <repository-url>
cd madushani_xai
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Run SHAP Analysis (Notebook 1)

```bash
cd ../notebooks
jupyter notebook 1_shap_temporal_drift.ipynb
```

This will:
- Load the trained XGBoost model
- Compute SHAP values per year (2020–2025) for 12 features
- Generate yearly rankings and drift statistics
- Save results to `backend/outputs/temporal_drift.json`

### 4. Run LIME Anomaly Diagnosis (Notebook 2)

```bash
jupyter notebook 2_lime_anomaly_diagnosis.ipynb
```

This will:
- Load the trained XGBoost model
- Generate LIME explanations for 15 representative demand instances
- Cover all demand levels: Low (3), Medium (4), High (4), Peak (4)
- Save results to `backend/outputs/anomaly_diagnosis.json`

### 5. Start the Backend API

```bash
cd ../backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 6. Install and Start the Frontend

```bash
cd ../frontend
npm install
npm run dev
```

### 7. Access the System

| Service | URL |
|---|---|
| React Dashboard | http://localhost:5173 |
| API Base URL | http://127.0.0.1:8000 |
| Swagger API Docs | http://127.0.0.1:8000/docs |
| Health Check | http://127.0.0.1:8000 |

---

## API Reference

Backend runs on port **8000**.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check / status |
| `GET` | `/api/temporal-drift` | SHAP feature importance per year (2020–2025) with rankings, drift, and the model comparison table |
| `GET` | `/api/anomaly-diagnosis` | 15 LIME explanations across all demand levels with feature contributions |
| `GET` | `/api/explain-date?date=YYYY-MM-DD` | Live LIME explanation for the highest-demand reading of a historical date. Returns 404 if the date is not in the dataset (2020-01-01 to 2025-05-31), 422 for an invalid date |

Each LIME contribution has `feature`, `rule` (LIME's quartile range, e.g. `Temperature > 29.29`), `weight` (kW) and `value`. Each instance also has `intercept` and `local_pred`, where `local_pred = intercept + sum(weights)`.

### v2 comparison evidence

Produced by `experiments/model_and_xai_comparison.py`, which only reads the dataset and `xgb_model.pkl`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v2/model-comparison` | Seasonal naive vs Linear Regression vs Optuna-tuned Random Forest vs deployed XGBoost (holdout + 5-fold rolling-origin CV) |
| `GET` | `/api/v2/xai-comparison` | SHAP vs LIME scored against the known ground truth: attribution, fidelity, stability, agreement, runtime |
| `GET` | `/api/v2/temporal-drift` | Per-year SHAP of the deployed model with 20-resample bootstrap 95% CIs; drift flagged only when CIs do not overlap |
| `GET` | `/api/figures/<name>.png` | Figures for the above (`backend/outputs/figures/`) |

Three earlier endpoints (`/api/demand-reduction`, `/api/cohort-profiling`, `/api/trust-validator`) were removed — no notebook ever produced their data and they returned 404. Only the three endpoints above are real and demoable.

Interactive API documentation (Swagger UI): **http://127.0.0.1:8000/docs**

---

## Dashboard Features

### 01 — SHAP Temporal Drift

| Feature | Description |
|---|---|
| **KPI Cards** | Most Dominant Feature, Biggest Gainer, Biggest Decline, Years Analysed |
| **Feature Trend Line Chart** | SHAP importance over time per feature (2020–2025); toggleable per feature. Temperature is hidden by default, with a note explaining why, because its scale (~157 kW) flattens every other line |
| **Yearly Ranking Cards** | Top 5 demand drivers identified for each year |
| **Drift Bar Chart** | Feature-level drift from 2020 to 2025 (blue = growth, red = decline); "Exclude Temperature" toggle, on by default |
| **Model Comparison** | Linear Regression vs Random Forest vs tuned XGBoost test metrics, plus XGBoost train/test metrics and Optuna summary |
| **Interpretation Guide** | How to read SHAP values, rising/falling trends, and feature crossings |

### 02 — LIME Anomaly Diagnosis

| Feature | Description |
|---|---|
| **Stats Row** | Total instances (15), Mean Demand, Std Demand, Peak Threshold (p90) |
| **Instance List (Left Panel)** | Filterable by demand level (All / Low / Medium / High / Peak); shows timestamp, badge, R², actual vs predicted |
| **Explanation Panel (Right Panel)** | Feature contributions as signed horizontal bars labelled with LIME's rule (e.g. `Temperature > 29.29`; green = positive, red = negative); local fit R² confidence bar; intercept and LIME local prediction |
| **Integration Hook** | Accepts `?source=bi&date=YYYY-MM-DD` from the Behaviour Intelligence dashboard and shows a live LIME explanation for that date (see below) |

---

### 03 — Model & XAI Comparison

Tables and figures from the v2 endpoints, with plain-English notes: why Linear Regression is exact on this dataset, and how that known ground truth is used to validate SHAP and LIME.

---

## Experiments (v2 evidence)

```bash
venv\Scripts\python.exe experiments\model_and_xai_comparison.py             # parts A–D
venv\Scripts\python.exe experiments\model_and_xai_comparison.py --parts B   # one part
venv\Scripts\python.exe experiments\dataset_check.py                       # cross-dataset check only
```

| Part | What it does | Output |
|---|---|---|
| A | Forecasting-model comparison on the notebook-1 split; Random Forest tuned with the same Optuna budget as XGBoost; 5-fold rolling-origin CV | `backend/outputs/v2/model_comparison_v2.json`, `figures/model_comparison_rmse_mape.png` |
| B | SHAP vs LIME on the deployed model, against the ground truth `Load = 100·T − 1300` | `v2/xai_comparison.json`, SHAP beeswarm/bar/dependence, LIME examples, LIME stability, comparison table |
| C | Temporal drift with one fixed model and bootstrap CIs | `v2/temporal_drift_v2.json`, `figures/temporal_drift_v2.png` |
| D | Cross-dataset check behind `DATASET_CHECK.md` | `v2/dataset_check.json` |

Seeds are fixed (42). The script never retrains or overwrites `xgb_model.pkl`, `temporal_drift.json` or `anomaly_diagnosis.json`.

---

## Notebooks

| Notebook | Purpose |
|---|---|
| `1_shap_temporal_drift.ipynb` | Compute SHAP values per year, extract rankings, detect temporal drift, export JSON |
| `2_lime_anomaly_diagnosis.ipynb` | Generate LIME explanations for 15 instances across all demand levels, export JSON |

---

## Integration with Other Components

The LIME Anomaly Diagnosis page supports direct deep-linking from **Component 1 (Behaviour Intelligence)**. When a user clicks the XAI button for an abnormal day on the Behaviour Intelligence dashboard, it opens this component for that date:

```
http://localhost:5173/anomaly-diagnosis?source=bi&date=2023-07-15
```

The page calls `/api/explain-date` and shows a live LIME explanation for that day's highest-demand 15-minute reading, full width, with a "Back to Dashboard" link. If the date is not in the dataset, it says so ("No historical data for …") rather than showing an unrelated sample.

Demand values come from `load_forecasting_dataset_corrected.csv`, which differs from the dataset Behaviour Intelligence analyses, so kW values for the same date can differ between the two dashboards.

The Future Behaviour Prediction flow can use `?source=bi-predict&date=<matched historical date>&future_date=<future date>`. This puts the live explanation at the top of the normal instance list.

---

## License

This project is developed for academic research purposes at SLIIT. All rights reserved.
