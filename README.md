# AI-Based Electricity Demand Behaviour Intelligence System

**Component 1 — Behaviour Intelligence**  
**Research Project | Sri Lanka Institute of Information Technology (SLIIT)**

---

## Project Information

| Field | Details |
|---|---|
| **Student** | Thanujan T |
| **Student ID** | IT22545176 |
| **Institution** | Sri Lanka Institute of Information Technology (SLIIT) |
| **Supervisor** | Dr. Nathali Silva |
| **Research Component** | Component 1 — Electricity Demand Behaviour Intelligence |

---

## Overview

This system applies machine learning and behavioural analytics to model, classify, and forecast electricity demand patterns at the consumer level. By analysing historical consumption data alongside contextual features such as time-of-day, day-of-week, and seasonality, the system identifies distinct demand behaviour archetypes and generates short-term load forecasts.

The insights produced enable utility providers and energy managers to:
- Optimise load scheduling and reduce peak-demand stress on the grid
- Support data-driven demand-response strategies
- Detect abnormal consumption patterns automatically
- Forecast future behaviour using historical seasonal matching

---

## System Architecture

```
Raw CSV Data
     │
     ▼
┌─────────────────────────────────────────┐
│           ML Training Pipeline          │
│  1. Data Loading & Column Detection     │
│  2. Preprocessing & Cleaning            │
│  3. 96-Slot Daily Profile Generation    │
│  4. K-Means & DBSCAN Clustering         │
│  5. Isolation Forest Anomaly Detection  │
│  6. Peak Demand Detection               │
│  7. Behaviour Labeling                  │
│  8. Model Evaluation & Export           │
└─────────────────┬───────────────────────┘
                  │  Trained .pkl Models + Processed CSVs
                  ▼
┌─────────────────────────────────────────┐
│        FastAPI Backend (Port 8001)      │
│  - Pipeline Controller                  │
│  - Analysis Service                     │
│  - REST API Endpoints                   │
└─────────────────┬───────────────────────┘
                  │  JSON Responses
                  ▼
┌─────────────────────────────────────────┐
│      React Frontend (Port 3000)         │
│  - KPI Dashboard                        │
│  - Recharts Visualisations              │
│  - Future Behaviour Prediction Panel    │
└─────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Core language |
| FastAPI | 0.111.0 | REST API framework |
| Uvicorn | 0.29.0 | ASGI server |
| scikit-learn | 1.4.2 | ML models (K-Means, DBSCAN, Isolation Forest) |
| pandas | 2.2.2 | Data processing |
| numpy | 1.26.4 | Numerical computation |
| scipy | 1.13.0 | Statistical analysis |
| Pydantic | 2.7.1 | Data validation & schemas |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 18.3.1 | UI framework |
| Vite | 5.0.0 | Build tool & dev server |
| Recharts | 2.12.7 | Data visualisation charts |
| Axios | 1.7.2 | HTTP client for API calls |

---

## Project Structure

```
behaviour-intelligence/
│
├── backend/
│   └── app/
│       ├── main.py                     # FastAPI app entry point, CORS config
│       ├── api/
│       │   └── routes.py               # All API endpoint definitions
│       ├── controllers/
│       │   └── pipeline_controller.py  # Orchestrates ML pipeline steps
│       ├── core/
│       │   └── config.py               # Path constants and configuration
│       ├── ml/
│       │   ├── train_models.py         # Standalone 8-step training script
│       │   ├── pipeline_runner.py      # Full pipeline executor function
│       │   ├── data_loader.py          # CSV loader with auto column detection
│       │   ├── preprocessing.py        # Data cleaning & 15-min resampling
│       │   ├── daily_profile.py        # 96-slot daily profile generation
│       │   ├── clustering.py           # K-Means & DBSCAN training
│       │   ├── anomaly_detection.py    # Isolation Forest & Z-score detection
│       │   ├── peak_detection.py       # Percentile-based peak identification
│       │   ├── behavior_labeling.py    # Rule-based behaviour classification
│       │   ├── behavior_prediction.py  # Future behaviour forecasting
│       │   └── verify_pkl_models.py    # Model file verification utility
│       ├── schemas/
│       │   └── response_models.py      # Pydantic API response models
│       └── services/
│           └── analysis_service.py     # Dashboard & profile data queries
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                     # Main dashboard component
│   │   ├── App.css                     # Dashboard styles (dark theme)
│   │   ├── FutureBehaviorPrediction.jsx # Future prediction UI panel
│   │   └── main.jsx                    # Vite entry point
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── raw/
│   │   └── load_forecasting_dataset_corrected.csv  # Input dataset
│   └── processed/                      # Auto-generated during training
│       ├── cleaned_data.csv
│       ├── daily_profiles.csv
│       ├── clustering_results.csv
│       ├── anomaly_results.csv
│       ├── peak_demand_results.csv
│       └── behavior_labels.csv
│
├── models/                             # Auto-generated during training
│   ├── profile_scaler.pkl
│   ├── kmeans_model.pkl
│   ├── dbscan_model.pkl
│   ├── isolation_forest_model.pkl
│   ├── clustering_metrics.json
│   ├── anomaly_metrics.json
│   └── behavior_label_summary.json
│
├── notebooks/
│   ├── 01_data_preprocessing.ipynb
│   ├── 02_daily_profile_generation.ipynb
│   ├── 03_clustering_model_training.ipynb
│   ├── 04_anomaly_detection_training.ipynb
│   └── 05_behavior_label_generation.ipynb
│
├── reports/
│   ├── training_pipeline_summary.md
│   └── model_training_outputs.md
│
├── requirements.txt
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- npm 9 or higher

### Step 1 — Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Verify Raw Data

Ensure the input dataset exists at:
```
data/raw/load_forecasting_dataset_corrected.csv
```
The dataset must contain a timestamp column and an electricity demand column.

### Step 3 — Train the ML Models

Run the complete 8-step training pipeline from the project root directory:

```bash
python backend/app/ml/train_models.py
```

This generates all processed CSVs in `data/processed/` and all model files in `models/`.

**Important:** Always run from the `behaviour-intelligence/` project root, not from any subdirectory.

### Step 4 — Start the Backend API

```bash
python -m uvicorn backend.app.main:app --reload --port 8001
```

### Step 5 — Install & Start the Frontend

```bash
cd frontend
npm install
npm start
```

### Step 6 — Access the System

| Service | URL |
|---|---|
| React Dashboard | http://localhost:3000 |
| API Base URL | http://127.0.0.1:8001 |
| API Documentation (Swagger) | http://127.0.0.1:8001/docs |
| Health Check | http://127.0.0.1:8001/health |

---

## ML Training Pipeline

The training pipeline runs 8 sequential steps:

| Step | Module | Description |
|---|---|---|
| 1 | `data_loader.py` | Load raw CSV; auto-detect timestamp and demand columns |
| 2 | `preprocessing.py` | Remove NaN/negatives/spikes; fill gaps; resample to 15-minute intervals |
| 3 | `daily_profile.py` | Convert time series to 96-slot daily profiles (1 slot = 15 minutes) |
| 4 | `clustering.py` | Train K-Means (auto k via silhouette score) and DBSCAN on normalised profiles |
| 5 | `anomaly_detection.py` | Run Isolation Forest (contamination = 3%) and Z-score (threshold = 3.0); combine with OR logic |
| 6 | `peak_detection.py` | Flag peak days: 90th percentile OR z-score > 2.0 OR anomaly + 75th percentile |
| 7 | `behavior_labeling.py` | Apply priority-based rules to assign one of four behaviour labels |
| 8 | Evaluation | Generate metrics JSON files and training summary report |

### Trained Model Files

| File | Description |
|---|---|
| `models/profile_scaler.pkl` | StandardScaler fitted on 96-slot daily profiles |
| `models/kmeans_model.pkl` | K-Means clustering model |
| `models/dbscan_model.pkl` | DBSCAN clustering model |
| `models/isolation_forest_model.pkl` | Isolation Forest anomaly detection model |

---

## Behaviour Classification

Each day is classified into one of four behaviour labels using a priority-based rule system:

| Label | Risk Level | Condition |
|---|---|---|
| **Abnormal Demand Day** | High | Anomaly detected AND not a peak demand day |
| **Peak Demand Day** | Medium | Peak value at 90th percentile OR z-score > 2.0 OR anomaly + 75th percentile |
| **Holiday / Low Demand Day** | Low | Mean daily demand below 25th percentile |
| **Normal Weekday Demand** | Normal | All other days |

---

## API Endpoints

All endpoints are prefixed with `/api`. The backend runs on port **8001**.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health check |
| `POST` | `/api/generate-daily-profiles` | Preprocess raw data and generate 96-slot daily profiles |
| `POST` | `/api/run-clustering` | Train K-Means and DBSCAN clustering models |
| `POST` | `/api/run-anomaly-detection` | Run Isolation Forest and Z-score anomaly detection |
| `POST` | `/api/detect-peak-days` | Identify peak demand days using percentile thresholds |
| `POST` | `/api/generate-behavior-labels` | Assign behaviour labels to all days |
| `GET` | `/api/dashboard-summary` | Return full KPI summary for the frontend dashboard |
| `GET` | `/api/predict-future-behavior?date=YYYY-MM-DD` | Predict behaviour label for a target date |
| `GET` | `/api/get-day-profile?date=YYYY-MM-DD` | Return the 96-slot load profile for a specific date |

Full interactive API documentation is available at: `http://127.0.0.1:8001/docs`

---

## Dashboard Features

The React frontend provides an interactive analytics dashboard with:

- **KPI Summary Cards** — Total days, Normal days, Peak days, Abnormal days, Holiday days
- **Label Distribution Pie Chart** — Clustering output breakdown
- **Risk Distribution Bar Chart** — Days by risk level
- **Top 15 Anomalous Days Chart** — Highest anomaly-scored days
- **Anomaly Score Trend** — 180-day rolling anomaly score line chart
- **All Days Explorer** — Paginated table of day-level records with details panel
- **96-Point Load Profile Viewer** — Full daily demand curve for any selected date
- **Future Behaviour Prediction Panel** — Date picker with seasonal matching-based prediction
- **XAI Integration** — LIME explainability output for abnormal days

---

## Model Verification

To verify that all trained model files are correctly saved and loadable:

```bash
python backend/app/ml/verify_pkl_models.py
```

---

## Additional Documentation

- [`reports/training_pipeline_summary.md`](reports/training_pipeline_summary.md) — Detailed training guide
- [`reports/model_training_outputs.md`](reports/model_training_outputs.md) — Model outputs and metrics
- [`notebooks/`](notebooks/) — Step-by-step Jupyter notebooks for each pipeline stage
