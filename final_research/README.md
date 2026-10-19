# AI-Based Electricity Demand Forecasting with Scenario Analysis

> **Component 3 — Demand Forecasting & Scenario Analysis Module**
> Final Year Research Project | Sri Lanka Institute of Information Technology (SLIIT)

---

## Research Information

| | |
|---|---|
| **Student Name** | Dewmini D.M.D.P |
| **Student ID** | IT22630216 |
| **Institution** | Sri Lanka Institute of Information Technology (SLIIT) |
| **Supervisor** | Dr. Nathali Silva |
| **Research Component** | Component 3 — Electricity Demand Forecasting with Scenario Analysis |
| **Academic Year** | 2025 / 2026 |

---

## Abstract

This component predicts electricity demand from weather, economic and calendar inputs, and lets a planner test "what-if" scenarios and see which parts of Sri Lanka could run short of supply. A Gradient Boosting model is trained on six years of 15-minute data (189,888 rows, 13 features) and (tuned with Optuna) reaches **R² = 0.824, MAE = 91.8 kW** on data it never saw during training. Prediction ranges are calibrated with split-conformal prediction (the 90% range contained 89.8% of unseen actual values). The model is served by a FastAPI backend and explored through a React dashboard with four tabs: **Predict**, **Scenarios**, **Grid Decision Lab** (a live risk map of Sri Lanka's nine provinces) and **Performance**.

> ### Data note — please read
> The dataset is **synthetic practice data**. The weather, economic and calendar columns come from the project's shared synthetic dataset. The target `Load Demand (kW)` was **regenerated** from explicit rules (daily load shape, air-conditioning load, weekend/holiday dips, price and GDP effects) plus random noise whose size was chosen in advance so that a good model scores about 0.8.
> The reported scores therefore demonstrate that the **method and evaluation are sound**; they are **not** accuracy on real Ceylon Electricity Board data. An earlier version of the dataset made demand an exact linear function of the inputs (R² = 0.99999, with Linear Regression scoring a perfect 1.0). That was recognised as leakage and replaced. Full provenance: [`backup_original_dataset/README.md`](backup_original_dataset/README.md).

---

## Research Problem & Motivation

Electricity demand is highly sensitive to temperature, time of day, prices and economic activity. Grid operators need (1) a forecast, (2) a way to test unusual conditions before they happen, and (3) an honest measure of how uncertain the forecast is. This component provides:

- a trained, evaluated forecasting model;
- a scenario engine (heat wave, cold spell, price shock, economic boom);
- calibrated uncertainty and an overload-risk map by province;
- a dashboard that non-technical stakeholders can use.

---

## Model Development & Comparison

The work follows a fixed order, and every parameter is defined in one configuration block at the top of `notebooks/1_model_training.ipynb` (mirrored in `scripts/train_model.py`).

**Step 1 — baseline comparison.** Three model families are trained on the identical 80/20 split (151,910 train rows, 37,978 test rows, `random_state=42`) with 13 input features and their initial parameters:

| Model | Initial parameters | Test R² | Test MAE (kW) | Test RMSE (kW) |
|---|---|---|---|---|
| Linear Regression | none | 0.438 | 160.1 | 205.5 |
| Random Forest | 100 trees, depth 10 | 0.777 | 102.9 | 129.5 |
| Gradient Boosting | 300 trees, depth 5, learning rate 0.08, subsample 0.8 | 0.825 | 91.5 | 114.6 |

Gradient Boosting builds trees one after another, each correcting the previous ones, so it captures curved relationships such as "air-conditioning only starts above about 26 °C", which Linear Regression cannot. It is the best family and is tuned next.

**Step 2 — Optuna hyperparameter tuning (training data only).** Optuna proposes parameter combinations from a defined search space (TPE sampler, seed 42) and scores each by 3-fold cross-validation on a 20,000-row sample of the **training** data; the test set is never used. Budget: 20 trials.

| Hyperparameter | Search range | Meaning |
|---|---|---|
| `n_estimators` | 100 to 300 (step 50) | number of trees |
| `max_depth` | 3 to 7 | how deep each tree can grow |
| `learning_rate` | 0.03 to 0.2 (log scale) | how strongly each tree corrects the last |
| `subsample` | 0.6 to 1.0 | share of rows each tree sees |
| `min_samples_leaf` | 5 to 80 (log scale) | smallest group of rows in a leaf |
| `max_features` | 0.5 to 1.0 | share of features tried at each split |

**Step 3 — choose by cross-validation, then evaluate once on the test set.** The tuned parameters are used only if they beat the initial ones in cross-validation (118.09 kW → 116.65 kW RMSE). The chosen model is refitted on the full training set.

| Deployed model parameter | Value |
|---|---|
| `n_estimators` | 250 |
| `max_depth` | 3 |
| `learning_rate` | 0.0984 |
| `subsample` | 0.860 |
| `min_samples_leaf` | 39 |
| `max_features` | 0.869 |

| Gradient Boosting | Test R² | Test MAE (kW) | Test RMSE (kW) |
|---|---|---|---|
| Initial parameters | 0.825 | 91.5 | 114.6 |
| **Optuna-tuned (deployed)** | **0.824** | **91.8** | **115.1** |

**Honest reading:** tuning improved the cross-validated score but the test score is essentially unchanged (difference of 0.001 in R²). Demand always contains some unpredictable variation, and the initial model was already close to that floor, so there was little left to gain. The tuned model is a little shallower (depth 3 instead of 5), which makes it smoother and slightly cheaper to run.

### Train vs test (overfitting check)

| | R² | MAE (kW) | RMSE (kW) |
|---|---|---|---|
| Train | 0.828 | 91.1 | 114.2 |
| Test | 0.824 | 91.8 | 115.1 |

Scores are close, so the model is not memorising. A **chronological** check (train on the first 80% of time, test on the last 20%) gives R² = **0.826**, so the result does not depend on a lucky random split.

### Input features (13)

| Category | Features |
|---|---|
| Weather | Temperature, Humidity, Wind Speed, Rainfall, Solar Irradiance |
| Economic | GDP, Per Capita Energy Use, Electricity Price |
| Calendar | Hour of Day, Day of Week, Month, Public Event, Poya Day |

Hour of day is the dominant feature (the daily rhythm is the biggest effect), followed by day of week, price and temperature.

---

## Uncertainty (split-conformal prediction)

A forecast is never exact, so the system also reports how wrong it can be.

1. The held-out test rows are split in half.
2. On the **calibration half** the error size that covers 90% of cases is found (about ±189 kW).
3. On the **evaluation half** that claim is checked.

| Range | Half-width | Actually contained |
|---|---|---|
| 80% | ± 147 kW | 79.9% |
| 90% | ± 189 kW | 89.8% |
| 95% | ± 225 kW | 95.0% |

The same error distribution gives the **overload probability** in the Grid Decision Lab: the chance that real demand ends up above the available supply.

---

## Scenario Analysis

A scenario changes some inputs and asks the same trained model again; the difference is the scenario's effect.

| Scenario | Parameters modified | Effect on demand |
|---|---|---|
| **Heat Wave** | Temperature +8 °C, Humidity −15 | +10.4% |
| **Cold Spell** | Temperature −10 °C, Humidity +20 | −4.3% |
| **Price Shock** | Electricity price ×2 | −7.2% |
| **Economic Boom** | GDP +20%, Per Capita Energy Use +10% | +7.7% |

Scenario results show direction and rough size as learned from the (synthetic) data; they are not proven real-world causes.

---

## Grid Decision Lab

A live map of Sri Lanka's nine provinces coloured by the chance of overload.

- **Filters:** day (today, weekday, weekend, Poya holiday) and weather (real weather now, normal, hot, heat wave).
- **Time of day:** slider, "Play day" button and a 24-hour strip showing when demand climbs.
- **Whole-country summary** plus a hover tooltip for each province.

How it works: today's real hourly temperature and humidity for each province capital (Open-Meteo) → the model predicts demand per province and hour → the overload chance is the probability that forecast error pushes demand above that province's capacity.

| Real | Modelled | Assumed (illustrative) |
|---|---|---|
| Province boundaries (geoBoundaries, CC BY 4.0); live weather | Demand from the trained model | Each province's share of national demand, its spare capacity, the 5–9 PM peak window, and the 2,300 kW national supply limit. The dataset has no regional information. |

The backend also exposes load-shifting, tariff and reserve levers with an auto-recommend search (`/api/recommend`); the screen currently shows the simplified map view.

---

## System Architecture

```
 scripts/generate_dataset.py -> dataset     notebooks/1 -> model + metadata + reference
 notebooks/2 -> conformal ranges            notebooks/3 -> scenario results
        │
        ▼
 backend/saved_models/  (forecast_model.pkl, model_metadata.json, reference.json,
                         conformal.json, performance.json)
        │
        ▼
 FastAPI backend  (port 8002)  ── Open-Meteo (live weather)
        │  JSON
        ▼
 React + Vite frontend  (port 5175)
   Predict | Scenarios | Grid Decision Lab | Performance
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn, scikit-learn, pandas, numpy, joblib |
| Modelling | scikit-learn, Optuna (hyperparameter tuning), matplotlib (notebooks) |
| Frontend | React 18, Vite 5, Tailwind CSS 3, Recharts, Axios |
| Data / maps | Open-Meteo (live weather), geoBoundaries (province shapes) |

---

## Project Structure

```
final_research/
├── backend/
│   ├── app.py                  # FastAPI app: model loading, predict, scenario endpoints
│   ├── grid_lab.py             # Grid Decision Lab: regions, live weather, risk, recommend
│   ├── requirements.txt
│   ├── saved_models/           # forecast_model.pkl + the JSON files the API reads
│   └── outputs/scenario_results.json
├── frontend/src/
│   ├── pages/ProfessionalDashboard.jsx   # four-tab dashboard (Predict, Scenarios)
│   ├── gridlab/                # Grid Decision Lab screen, map, risk colours
│   ├── components/PerformancePanel.jsx   # Performance tab
│   └── data/provinces.js       # province outlines for the map
├── notebooks/
│   ├── 1_model_training.ipynb
│   ├── 2_uncertainty_calibration.ipynb
│   ├── 3_scenario_analysis.ipynb
│   └── load_forecasting_dataset_corrected.csv
├── scripts/                    # command-line equivalents of the notebooks
│   ├── generate_dataset.py  train_model.py  calibrate.py  build_map.py
└── backup_original_dataset/    # provenance, original data/models/notebooks
```

---

## Notebooks

Run them in order. Each one is self-contained, commented, and ends with a summary; the `scripts/` files do the same work from the command line. The dataset is **not** built in a notebook: it is produced by `scripts/generate_dataset.py` (see the data note above) and the notebooks start from the saved CSV.

| Notebook | Purpose | Writes |
|---|---|---|
| `1_model_training.ipynb` | Configuration of all parameters, EDA, 3-model comparison, **Optuna tuning** (cross-validated, training data only), final model, train-vs-test and chronological checks, diagnostics, feature importance, model export | `forecast_model.pkl`, `model_metadata.json`, `reference.json` |
| `2_uncertainty_calibration.ipynb` | Split-conformal ranges, coverage check, error distribution for the risk map | `conformal.json`, `performance.json` |
| `3_scenario_analysis.ipynb` | Four what-if scenarios, 24-hour heat-wave curve, sensitivity ranking | `scenario_results.json` |

All random seeds are fixed, so re-running reproduces the saved files.

---

## Setup & Run

Prerequisites: Python 3.11, Node.js 18+.

```bash
# backend
cd final_research
python3.11 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
pip install jupyter matplotlib optuna     # only needed to run the notebooks and scripts/train_model.py

# (optional) rebuild the data, then run the notebooks in order:
python scripts/generate_dataset.py
cd notebooks && jupyter notebook          # run 1, 2, 3 (notebook 1 takes about 7 minutes because of the Optuna search)

# start the API
cd ../backend && uvicorn app:app --host 0.0.0.0 --port 8002

# frontend (new terminal)
cd frontend && npm install && npm run dev
```

Or from the repository root: `python3 start-all.py --only forecast`.

| Service | URL |
|---|---|
| Dashboard | http://localhost:5175 |
| API docs (Swagger) | http://127.0.0.1:8002/docs |
| Health check | http://127.0.0.1:8002/api/health |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/model-info` | Model type, sample counts, metrics, feature list |
| `POST` | `/api/predict` | One demand prediction from the input features |
| `GET` | `/api/scenarios` | Pre-computed scenario results |
| `POST` | `/api/scenario-test` | Custom scenario (baseline + modifications) |
| `GET` | `/api/reference` | Input ranges, a typical day, default supply limit |
| `POST` | `/api/curve` | 24-hour demand curve for a baseline and a scenario |
| `POST` | `/api/explain` | One-factor-at-a-time attribution of a change |
| `POST` | `/api/sensitivity` | Low-to-high swing of each input |
| `POST` | `/api/decision` | Regional demand, 90% range and overload probability |
| `POST` | `/api/recommend` | Smallest load-shift / tariff mix meeting a risk target |
| `GET` | `/api/live-weather` | Live temperature and humidity for the nine province capitals |
| `GET` | `/api/performance` | Metrics and comparison for the Performance tab |

---

## Dashboard

| Tab | What it shows |
|---|---|
| **Predict** | Input form for the features; a single demand prediction |
| **Scenarios** | Baseline vs. four scenarios with percentage change, calculated live by the model |
| **Grid Decision Lab** | Filters, time-of-day control, demand strip, whole-country summary, province risk map, "how this works" |
| **Performance** | Train vs test and the three-model comparison |

---

## Limitations & Future Work

- Data is synthetic; scores demonstrate the method, not real-world accuracy.
- Regional demand shares, spare capacity and the supply limit are illustrative assumptions.
- The model has no lag features (previous-hour demand), so it cannot react to events absent from its inputs.
- Future work: real CEB load and provincial/substation data, lag features, comparison with the neural models of Component 2, and linking to the XAI component (Component 4) to explain individual forecasts.

---

## License

This project is developed for academic research purposes at SLIIT. All rights reserved.
