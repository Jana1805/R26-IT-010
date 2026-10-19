# Electricity Demand Sri Lanka - Architecture Report

Generated: 2026-08-07

## 1. Executive Summary

This project is a dataset-backed electricity demand forecasting system for Sri Lanka. In simple terms, it loads historical demand and weather-style features from CSV files, loads trained TensorFlow/Keras forecasting models from local artifacts, exposes forecast and analysis endpoints through FastAPI, and visualizes the results in a React dashboard.

Architecturally, it is a layered monolith rather than a microservice system. The backend, model serving logic, data loading logic, and API routes all run inside one FastAPI process. The frontend is a separate single-page application built with Vite and React, but it communicates with one backend API, not multiple independent services.

Current maturity: strong for a research/demo application, partially prepared for production, but not yet a production-grade live grid forecasting platform. The main missing pieces are live ingestion, persistent database storage, authentication, observability, automated tests, CI/CD, containerization, and operational model lifecycle management.

## 2. Project Architecture

### Simple Concept

The system has three main parts:

1. A React dashboard for users.
2. A FastAPI backend that exposes forecasting and analytics endpoints.
3. Local ML/data artifacts: CSV datasets, Keras models, scikit-learn scalers, notebooks, and generated output images.

### Internal Structure

The backend follows a layered monolith pattern:

```text
Browser
  |
  | HTTP GET requests through Vite proxy or configured API URL
  v
React SPA
  |
  | /api/* in local dev, rewritten to FastAPI
  v
FastAPI app
  |
  | routers: HTTP contracts
  | services: model loading, inference, feature engineering
  | core: config and process state
  v
CSV dataset + local .keras/.pkl artifacts
```

This is not microservices because:

- There is only one backend runtime.
- Model loading, routing, feature engineering, and cache state share the same Python process.
- There is no service discovery, message broker, independent database service, or independent deployable model service.

This is not a pure MVC application either. It is closer to a modular API backend plus SPA frontend. The backend uses routers for controllers, services for business/model logic, Pydantic schemas for contracts, and module-level state for loaded runtime objects.

## 3. Directory and Major File Purpose

### Root

| Path | Purpose | Notes |
|---|---|---|
| `README.md` | Main project overview and local run instructions | Clearly states the app is dataset-backed, not true real-time production. |
| `requirements.txt` | Python backend dependencies | FastAPI, Uvicorn, NumPy, pandas, scikit-learn, joblib, TensorFlow. |
| `docker-compose.yml` | Placeholder deployment file | Currently empty, so containerized deployment is not implemented. |
| `.gitignore` | Ignore rules | Ignores `.venv`, `__pycache__`, `.pyc`, `node_modules`, `.env`. Does not ignore large model/data artifacts. |
| `backend_logic_summary.txt` | Backend/model integration notes | Useful implementation summary for model registry, horizon handling, and inference paths. |
| `report.md` | This architecture report | New documentation output. |

### Backend: `api/`

| Path | Purpose | Notes |
|---|---|---|
| `api/main.py` | FastAPI application bootstrap | Creates `FastAPI`, configures CORS, includes routers, loads models/data on startup. |
| `api/core/config.py` | Central configuration and model registry | Defines paths, feature columns, forecast limits, CORS origins, model profiles, default model key. |
| `api/core/state.py` | Shared runtime state | Stores loaded models, scalers, raw dataframe, load errors, and simple in-memory caches. |
| `api/routers/forecast.py` | Forecast endpoint | Implements `/forecast` using selected model, autoregressive feature updates, uncertainty bands. |
| `api/routers/behaviour.py` | Health, data, demand, model, heatmap endpoints | Implements `/health`, `/data/range`, `/data/source`, `/demand/live`, `/demand/historical`, `/analysis/heatmap`, `/model/metrics`, `/models`, `/debug/health`. |
| `api/routers/scenario.py` | Scenario endpoint | Implements rule-based `/scenario` what-if estimate. |
| `api/services/model_loader.py` | Startup artifact loading | Loads Keras models, scalers, CSV data, custom objects, and warms models up. |
| `api/services/inference.py` | Inference helpers | Handles MC Dropout prediction, vector multi-step prediction, inverse scaling, conformal intervals. |
| `api/services/feature_engineering.py` | Runtime feature creation | Builds cyclical time features, lag features, rolling statistics, and autoregressive forecast rows. |
| `api/services/custom_layers.py` | Keras custom layers | Defines `PositionalEncoding` and `TransformerBlock` for model deserialization. |
| `api/services/model_evaluation.py` | Evaluation utilities | Can compute train/val/test metrics and conformal calibration from loaded data/models. Not currently wired into main endpoints except conceptually. |
| `api/schemas/response.py` | Pydantic response models | Defines typed API response contracts and OpenAPI schema generation. |
| `api/schemas/query.py` | Query parameter models | Present but mostly unused; routers currently declare query params directly with FastAPI `Query`. |
| `api/utils/sanitizers.py` | Numeric safety helpers | Converts invalid floats and recursively sanitizes response payloads. |

### Frontend: `frontend/`

| Path | Purpose | Notes |
|---|---|---|
| `frontend/package.json` | Frontend dependencies and scripts | React 19, Vite 8, Recharts, lucide-react, Axios dependency present but fetch is used. |
| `frontend/vite.config.js` | Vite config | Proxies `/api` to `http://127.0.0.1:8000` in local development. |
| `frontend/index.html` | SPA HTML entry | Mounts the React app. |
| `frontend/src/main.jsx` | React root bootstrap | Renders `<App />` inside `StrictMode`. |
| `frontend/src/App.jsx` | Main dashboard composition | Provides header, stats row, tabs, and tab routing with local state. |
| `frontend/src/App.css` | Global dashboard styling | Contains layout, panels, tables, charts, responsive rules. |
| `frontend/src/api.js` | API client wrapper | Centralizes `fetch` calls, timeout handling, and endpoint URL construction. |
| `frontend/src/hooks/useAppData.js` | Frontend data orchestration | Loads health/source/range/live/historical/heatmap/model data and controls forecast/scenario actions. |
| `frontend/src/components/Header.jsx` | Header component | Shows app name, API status, mode badge, latest dataset demand. |
| `frontend/src/components/UI.jsx` | Shared UI primitives | Stat card, chart tooltip, status pill, inline error, metric box. |
| `frontend/src/tabs/*.jsx` | Dashboard feature tabs | Forecast, behaviour heatmap, model metrics, scenario simulator. |
| `frontend/public/*` and `frontend/src/assets/*` | Static assets | Icons and images. |

### Data and ML Artifacts

| Path | Purpose | Notes |
|---|---|---|
| `data/electricity_demand_srilanka_fixed.csv` | Active backend dataset | Configured as `DATA_PATH`; about 189,888 rows plus header at inspection time. |
| `data/electricity_demand_srilanka.csv` | Alternate dataset copy | Similar size; not the active backend default in current config. |
| `outputs/` | Generated artifacts and earlier default model outputs | Contains model/scaler files, plots, and copied CSV. Some README paths are older than current config. |
| `models/CNN-LSTM(Final)/` | Final CNN-LSTM model artifacts | Active default model path for `mc_dropout`. |
| `models/CNN-LSTM(B)-With all data/` | Baseline CNN-LSTM artifacts | Registered as deterministic `baseline`. |
| `models/Transformer(B) Final/` | Transformer baseline artifacts | Registered as `transformer_baseline`; includes metrics/config JSON. |
| `models/TransformerCNN(Final)/` | CNN-Transformer artifacts | Registered as `cnn_transformer`; includes summary and plots. |
| `notebooks/` | Notebook workspace | Currently no files visible in this directory, but model notebooks live under `models/*`. |
| `src/` | Research/package skeleton | Most modules are empty placeholders except `src/models/transformer.py`. Active serving code is under `api/`. |
| `tests/` | Test directory | Currently empty. |
| `docs/` | Existing project notes | Production notes, API refactor summary, and forecast optimization notes. Some examples are stale. |

## 4. Frontend and Backend Technologies

### Backend

The backend uses:

- Python
- FastAPI for HTTP API routing and OpenAPI docs
- Uvicorn as ASGI server
- Pydantic for response schema validation
- pandas and NumPy for time-series data processing
- scikit-learn scalers loaded with joblib
- TensorFlow/Keras for model loading and inference
- Module-level in-memory state for loaded artifacts and simple forecast cache

Practical example:

```bash
python -m uvicorn api.main:app --reload --port 8000
```

### Frontend

The frontend uses:

- React 19
- Vite 8
- Recharts for charts
- lucide-react for icons
- Native `fetch` with `AbortController` for API calls
- CSS modules through a global `App.css` file

Practical example:

```bash
cd frontend
npm install
npm run dev
```

### Important Observation

`axios` is listed in `frontend/package.json`, but `frontend/src/api.js` uses native `fetch`. That is not a runtime bug, but it is dependency noise and should be cleaned up unless Axios will be used intentionally.

## 5. Data Model, Database Design, and Data Flow

### Current Data Storage

There is no database in the current implementation. Data is stored as CSV files and loaded into memory at backend startup.

The active dataset path is:

```text
data/electricity_demand_srilanka_fixed.csv
```

The CSV includes timestamped demand and feature columns such as:

- Timestamp
- Weather inputs: temperature, humidity, wind speed, rainfall, solar irradiance
- Economic/context inputs: GDP, per-capita energy use, electricity price
- Calendar inputs: day of week, hour of day, month, season, public event, Poya day
- Target: load demand in kW

The backend feature engineering layer derives model-ready features:

- Cyclical time encodings: `sin_hour`, `cos_hour`, `sin_dow`, `cos_dow`, `sin_month`, `cos_month`
- Calendar flags: `is_weekend`, `Public Event`, `Poya Day`
- Normalized year: `year_norm`
- Demand lags: `load_lag_96`, `load_lag_192`, `load_lag_672`
- Rolling statistics: `load_mean_week`, `load_std_day`

### Current Data Flow

```text
CSV file
  -> pandas read_csv on FastAPI startup
  -> engineer_features()
  -> dataframe stored in api.core.state.RAW_DF
  -> endpoints slice/aggregate dataframe
  -> forecast endpoint builds model input window
  -> scaler transforms features
  -> Keras model predicts demand
  -> target scaler inverse-transforms prediction
  -> JSON response returned to React
```

### Internal Forecast Flow

For a forecast request:

1. Validate the requested model and data are available.
2. Choose an anchor timestamp, either latest data or selected historical timestamp.
3. Extract the last model lookback window.
4. Scale the feature matrix.
5. Run model prediction:
   - deterministic model: one forward pass
   - MC Dropout model: multiple stochastic forward passes
6. Convert predicted scaled values back to kW.
7. Add conformal intervals if the model supports uncertainty.
8. Create synthetic future feature rows using autoregressive predicted demand.
9. Repeat until the requested horizon is reached.

### Recommended Production Database Design

For production, replace CSV-only storage with a normalized time-series schema.

Example relational schema:

```sql
CREATE TABLE demand_observations (
  id BIGSERIAL PRIMARY KEY,
  timestamp_utc TIMESTAMPTZ NOT NULL UNIQUE,
  demand_kw NUMERIC(12, 3) NOT NULL,
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE weather_observations (
  id BIGSERIAL PRIMARY KEY,
  timestamp_utc TIMESTAMPTZ NOT NULL,
  region_code TEXT NOT NULL,
  temperature_c NUMERIC(6, 3),
  humidity_pct NUMERIC(6, 3),
  wind_speed_mps NUMERIC(6, 3),
  rainfall_mm NUMERIC(8, 3),
  solar_irradiance_w_m2 NUMERIC(10, 3),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (timestamp_utc, region_code)
);

CREATE TABLE calendar_events (
  id BIGSERIAL PRIMARY KEY,
  event_date DATE NOT NULL,
  event_type TEXT NOT NULL,
  name TEXT,
  is_public_event BOOLEAN NOT NULL DEFAULT false,
  is_poya_day BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (event_date, event_type, name)
);

CREATE TABLE model_versions (
  id BIGSERIAL PRIMARY KEY,
  model_key TEXT NOT NULL,
  version TEXT NOT NULL,
  artifact_uri TEXT NOT NULL,
  feature_schema_version TEXT NOT NULL,
  trained_from TIMESTAMPTZ,
  trained_to TIMESTAMPTZ,
  metrics_json JSONB NOT NULL DEFAULT '{}',
  is_active BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (model_key, version)
);

CREATE TABLE forecast_runs (
  id BIGSERIAL PRIMARY KEY,
  model_version_id BIGINT NOT NULL REFERENCES model_versions(id),
  anchor_timestamp_utc TIMESTAMPTZ NOT NULL,
  steps INT NOT NULL,
  n_passes INT NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE forecast_points (
  id BIGSERIAL PRIMARY KEY,
  forecast_run_id BIGINT NOT NULL REFERENCES forecast_runs(id),
  timestamp_utc TIMESTAMPTZ NOT NULL,
  forecast_kw NUMERIC(12, 3) NOT NULL,
  lower_95_kw NUMERIC(12, 3),
  upper_95_kw NUMERIC(12, 3),
  mc_std_kw NUMERIC(12, 3),
  actual_kw NUMERIC(12, 3),
  UNIQUE (forecast_run_id, timestamp_utc)
);
```

Recommended indexes:

```sql
CREATE INDEX idx_demand_timestamp ON demand_observations (timestamp_utc);
CREATE INDEX idx_weather_region_timestamp ON weather_observations (region_code, timestamp_utc);
CREATE INDEX idx_forecast_runs_anchor ON forecast_runs (anchor_timestamp_utc);
CREATE INDEX idx_forecast_points_timestamp ON forecast_points (timestamp_utc);
```

Why this design:

- Demand, weather, calendar, model versions, and forecast outputs have separate lifecycle concerns.
- Time-based indexes support fast historical windows and lag calculations.
- Model versioning makes forecasts auditable.
- `forecast_runs` plus `forecast_points` preserves generated predictions rather than recalculating everything.

## 6. API Structure and Communication Patterns

### Endpoint Surface

The active API uses REST-style GET endpoints:

| Endpoint | Method | Purpose |
|---|---:|---|
| `/health` | GET | Backend readiness, model/data/scaler status, feature metadata |
| `/data/range` | GET | Dataset min/max timestamps and safe forecast start |
| `/data/source` | GET | Demo/live source metadata and freshness |
| `/demand/live` | GET | Latest recorded dataset demand |
| `/demand/historical` | GET | Historical demand slice |
| `/analysis/heatmap` | GET | Average demand by hour and day of week |
| `/model/metrics` | GET | Model profile, metrics, uncertainty information |
| `/models` | GET | Available model keys and display names |
| `/debug/health` | GET | Raw debug health payload |
| `/forecast` | GET | Model forecast with optional actual comparison |
| `/scenario` | GET | Rule-based what-if estimate |

### Communication Pattern

Frontend communication is synchronous request/response:

```javascript
api.forecast({
  steps: 24,
  startTimestamp: selectedTs,
  includeActuals: true,
  model: selectedModel
});
```

In local development, the frontend calls `/api/...`; Vite proxies that to FastAPI and strips `/api`.

```text
React fetch('/api/forecast?...')
  -> Vite proxy
  -> http://127.0.0.1:8000/forecast?...
  -> FastAPI router
  -> service/model layer
  -> JSON response
```

### API Design Observations

Good:

- Response models are defined with Pydantic.
- Query limits exist for forecast steps and historical window size.
- Feature mismatch checks prevent silently invalid model input.
- API client has timeout handling.

Needs improvement:

- All operations are GET, including compute-heavy forecast/scenario work. Forecast could remain GET if it is idempotent, but a POST is more flexible for complex request bodies.
- `api/schemas/query.py` is mostly unused, which creates drift between declared query models and actual route signatures.
- Existing docs include stale examples showing POST `/forecast`, while the actual endpoint is GET.
- Error responses are not standardized across endpoints beyond FastAPI defaults.
- Long-running inference is synchronous and ties up request workers.

## 7. Authentication and Authorization

### Current State

There is no authentication or authorization mechanism in the current codebase.

There are no visible:

- Login flows
- Password storage
- API keys
- JWT validation
- OAuth/OIDC integration
- Role-based access controls
- FastAPI `Depends` auth dependencies

### Risk Level

For a local demo, this is acceptable. For a public or institutional deployment, this is a high-priority gap.

Endpoints such as `/health`, `/debug/health`, `/model/metrics`, and `/forecast` reveal operational details about data freshness, available models, feature counts, load errors, and potentially expensive inference behavior.

### Recommended Auth Design

For a production dashboard:

- Use OIDC/OAuth through an identity provider for users.
- Protect all application endpoints except a minimal public health check.
- Add role-based access:
  - Viewer: read forecasts and dashboards.
  - Analyst: run scenario and comparison forecasts.
  - Admin: manage model versions, data providers, and deployment settings.
- Use short-lived access tokens.
- Add server-side authorization checks with FastAPI dependencies.

Example FastAPI dependency shape:

```python
from fastapi import Depends, HTTPException, status

def require_role(required_role: str):
    def dependency(current_user = Depends(get_current_user)):
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return dependency
```

## 8. Code Organization and Maintainability

### Strengths

- Backend code has been refactored into clear layers:
  - `core` for configuration/state
  - `routers` for HTTP endpoints
  - `services` for model/data/inference logic
  - `schemas` for response contracts
  - `utils` for shared helpers
- Frontend API calls are centralized in `frontend/src/api.js`.
- Frontend data loading is centralized in `useAppData`.
- Model registry in `api/core/config.py` makes multi-model serving possible.
- Model-specific differences such as horizon, uncertainty support, and mixed precision are represented declaratively.

### Maintainability Issues

1. Runtime state is stored in module-level globals.

   This is simple, but it makes multi-process deployments, testing, hot reload behavior, and cache invalidation harder.

2. The active serving package and research package are split.

   `api/` contains active serving logic. `src/` mostly contains empty placeholders, except transformer custom layer code. This can confuse future contributors about the source of truth.

3. Duplicate custom layer definitions exist.

   `api/services/custom_layers.py` and `src/models/transformer.py` both define Transformer layer classes. Divergence here can break model loading or produce subtle inference differences.

4. Some UI model information is hard-coded.

   `ModelTab.jsx` contains static epoch history, architecture layers, and progress items. Meanwhile, `/model/metrics` returns model metadata. This creates drift when the selected model changes.

5. Query schemas exist but are not wired.

   `api/schemas/query.py` declares request/query models, but routers currently define individual query parameters directly.

6. Existing docs have stale examples.

   `docs/API_REFACTOR.md` references POST `/forecast` and historical query parameters that do not match current route signatures.

7. Tests are missing.

   `tests/` is empty. The project currently relies on manual smoke testing.

### Practical Refactoring Example

Move duplicated Transformer custom objects into one source:

```text
src/models/transformer.py
  -> canonical model layer definitions

api/services/custom_layers.py
  -> imports from src.models.transformer instead of redefining classes
```

This reduces risk that training-time and serving-time definitions diverge.

## 9. Scalability and Performance Considerations

### Current Performance Profile

The app loads all data, models, and scalers into memory at startup. Forecast requests are synchronous. For deterministic forecasts this can be acceptable. For MC Dropout forecasts, latency grows with:

- Number of forecast steps
- Number of MC passes
- Model complexity
- CPU/GPU availability
- Whether the model is single-step or multi-step

The code already includes some pragmatic optimizations:

- Model warm-up during startup
- Forecast query limits
- Reduced default MC samples
- Batched MC inference
- Simple one-entry forecast cache

### Bottlenecks

1. Synchronous inference blocks the request worker.

   Heavy forecast requests can hold a FastAPI worker for a long time.

2. Module-level state does not scale cleanly across workers.

   If Uvicorn/Gunicorn uses multiple workers, each process loads its own copy of all models and CSV data. That increases memory usage.

3. Forecast cache is minimal.

   `FORECAST_CACHE` is cleared on every new forecast and stores only one recent payload effectively. It is not a real multi-key LRU cache.

4. CSV data is loaded fully into memory.

   Fine for about 190k rows, but not ideal for live production or multi-year high-resolution data growth.

5. Repeated `pd.concat` inside forecast loops can become inefficient.

   The current forecast horizons are bounded, so this is not catastrophic. Still, list accumulation followed by one dataframe construction would be cleaner for longer horizons.

6. No background jobs.

   Long forecasts, batch evaluations, or retraining jobs should not run inside request/response paths.

### Scalability Recommendations

- Introduce a forecast job API for expensive inference:

```text
POST /forecast-runs
  -> returns job_id

GET /forecast-runs/{job_id}
  -> returns queued/running/completed/failed

GET /forecast-runs/{job_id}/points
  -> returns forecast output
```

- Store forecast results in a database so common views load instantly.
- Use Redis or another shared cache if multiple API workers are used.
- Use a model serving layer for production, such as a dedicated TensorFlow Serving process or a separate inference worker pool.
- Precompute common horizons periodically.
- Add metrics for inference latency, model load time, cache hit rate, memory, and request failures.

## 10. Security Vulnerabilities and Risks

### Key Risks

1. No authentication or authorization.

   Any user who can reach the API can call all endpoints.

2. Debug endpoint exposure.

   `/debug/health` exposes raw operational state and should not be public.

3. Broad local CORS behavior.

   The backend allows configured origins and a regex for localhost/127.0.0.1 ports. This is helpful for development, but production should use exact allowed origins only.

4. Expensive endpoint abuse.

   `/forecast` can trigger TensorFlow inference. Although limits exist, unauthenticated repeated calls can still consume CPU/GPU and memory.

5. Artifact path loading.

   Models and scalers are loaded from local paths and environment-configurable model/scaler paths. This is operationally useful, but production should validate artifact source, permissions, signatures, and path scope.

6. Pickle/joblib artifact risk.

   `joblib.load` can execute unsafe serialized Python objects if artifacts are untrusted. Only load scalers from trusted, controlled storage.

7. Missing security headers and deployment boundary.

   There is no visible reverse proxy, TLS termination, CSP, HSTS, or secure cookie configuration because no auth/session layer exists yet.

8. Data integrity risk.

   CSV input is trusted. There is no explicit schema validation for required raw input columns before feature engineering beyond failures during processing.

9. Information leakage in error responses.

   Some errors include model names, path-related load failures, feature mismatches, and internal exception messages.

### Prevention Examples

Recommended middleware/dependency layer:

```python
@router.get("/debug/health", dependencies=[Depends(require_role("admin"))])
def debug_health():
    ...
```

Recommended production CORS:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://edis.example.gov.lk"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

Recommended artifact policy:

- Store models in versioned object storage.
- Verify checksum before loading.
- Never load user-uploaded `.pkl`, `.joblib`, or `.keras` artifacts directly.
- Run inference under a least-privilege service account.

## 11. Recommended Improvements and Refactoring Opportunities

### Priority 1: Production Safety

1. Add authentication and role-based authorization.
2. Remove or protect `/debug/health`.
3. Add rate limiting for expensive endpoints.
4. Restrict CORS in production.
5. Add structured logging, request IDs, and sanitized error responses.

### Priority 2: Data and Model Reliability

1. Replace CSV-only data access with a database-backed provider layer.
2. Add raw data schema validation before feature engineering.
3. Version feature schemas and validate feature order against model metadata.
4. Add a model registry table or manifest that tracks model version, metrics, artifact checksums, training window, and active status.
5. Move forecast outputs into durable storage for auditability.

### Priority 3: Codebase Maintainability

1. Make one canonical Transformer custom-layer module.
2. Remove or complete empty `src/` placeholders.
3. Wire `api/schemas/query.py` into FastAPI dependencies or remove it.
4. Move hard-coded UI model metadata into API responses or static versioned JSON.
5. Normalize docs so examples match current endpoints.
6. Consider TypeScript for frontend contract safety.

### Priority 4: Performance and Scalability

1. Add background forecast jobs for long-running inference.
2. Add a proper LRU/shared cache for repeated forecasts.
3. Precompute common forecast horizons.
4. Profile inference by model key, horizon, and MC passes.
5. Consider GPU-backed inference workers or TensorFlow Serving.
6. Avoid repeated dataframe concatenation in forecast loops if horizons increase.

### Priority 5: Testing and Quality Gates

1. Add fast unit tests for feature engineering.
2. Add API contract tests with mocked model/scaler state.
3. Add frontend component tests for tab behavior and error states.
4. Add smoke tests for `/health`, `/models`, `/data/range`, and a mocked `/forecast`.
5. Add CI checks for backend lint/test and frontend lint/build.

## 12. Development Workflow

### Current Local Workflow

Backend:

```bash
python -m uvicorn api.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Local request flow:

```text
Vite frontend: http://localhost:5173
  -> /api proxy
  -> FastAPI backend: http://127.0.0.1:8000
```

### Current Strengths

- Local setup is simple.
- Vite proxy reduces CORS friction in development.
- README documents important environment variables.
- Model registry supports multiple models without duplicating endpoint code.

### Current Gaps

- `docker-compose.yml` is empty.
- No Dockerfiles are present.
- No CI/CD configuration is visible.
- No automated test suite is implemented.
- No environment-specific configuration files or deployment manifests are visible.
- No production ASGI process manager configuration is present.

## 13. Recommended Deployment Workflow

### Practical Production Path

1. Build backend container:
   - Python slim image
   - Install pinned dependencies
   - Copy API code
   - Mount or download model artifacts at startup
   - Run Uvicorn/Gunicorn with controlled worker count

2. Build frontend container:
   - Run `npm ci`
   - Run `npm run build`
   - Serve static files through Nginx or a platform static host

3. Add infrastructure services:
   - PostgreSQL or TimescaleDB for time-series persistence
   - Redis for shared cache and background job queue
   - Object storage for model artifacts
   - Observability stack for logs, metrics, and alerts

4. Add CI/CD:
   - Backend lint/test
   - Frontend lint/build
   - Dependency audit
   - Container build
   - Smoke test against deployed staging
   - Promotion to production only after health checks pass

Example production service split:

```text
frontend-static
  -> serves React build

api-service
  -> FastAPI routes, auth, lightweight reads

forecast-worker
  -> heavy TensorFlow inference jobs

database
  -> demand, weather, forecasts, model metadata

object-storage
  -> versioned model and scaler artifacts
```

## 14. Common Mistakes to Avoid

1. Calling this a live production monitor when the current source is a static historical dataset.
2. Exposing `/debug/health` publicly.
3. Loading untrusted `.pkl` or `.joblib` artifacts.
4. Letting frontend hard-coded model metrics drift from backend model metadata.
5. Scaling API workers without accounting for each worker loading every model into memory.
6. Treating model files and scalers as unversioned local files.
7. Running long TensorFlow inference inside synchronous request handlers at high traffic.
8. Keeping stale API documentation after endpoint signatures change.
9. Ignoring feature order and feature schema versioning.
10. Adding a database later without preserving timestamp uniqueness and model version audit trails.

## 15. Industry Best Practices for This Type of System

### API and Backend

- Keep routers thin and put domain/model logic in services.
- Use dependency injection for loaded services, auth, and request context.
- Standardize errors with an error schema.
- Add request IDs and structured JSON logs.
- Protect expensive endpoints with auth and rate limits.
- Separate debug/admin endpoints from public API routes.

### Data and ML

- Version every model, scaler, and feature schema together.
- Store model artifacts in controlled object storage with checksums.
- Keep training, validation, and inference feature generation consistent.
- Persist forecasts with model version and anchor timestamp for auditability.
- Monitor prediction drift, data freshness, missing features, and forecast error once actuals arrive.

### Frontend

- Generate or share API types from OpenAPI, preferably with TypeScript.
- Keep model metrics and architecture displays data-driven.
- Show loading, failure, stale-data, and degraded-backend states clearly.
- Avoid hidden assumptions in UI labels, especially around "live" vs "dataset demo".

### Operations

- Containerize backend and frontend.
- Use separate staging and production environments.
- Use CI/CD with tests, linting, builds, and smoke checks.
- Monitor latency, error rates, memory, model load failures, and stale input data.
- Use background workers for slow inference and batch evaluation.

## 16. Overall Assessment

The project is well suited as a research demonstration and dashboard prototype. The strongest architectural decision is the recent backend layering around `api/core`, `api/services`, `api/routers`, and `api/schemas`, because it gives the project a clean path from notebook-driven work toward a maintainable API.

The biggest architectural gap is that the system still serves local static data and local ML artifacts directly from one backend process. That is acceptable for demos, but production should introduce authenticated access, live data ingestion, database persistence, artifact versioning, background inference jobs, observability, and automated tests.

The next best engineering move is to add tests and contract validation around the current API before larger refactors. After that, introduce a provider abstraction for data access so the same endpoints can work against either the current dataset-backed demo or a real live data source without changing the frontend.
