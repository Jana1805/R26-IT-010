# electricity-demand-sri-lanka

Electricity Demand Intelligence System (EDIS) for Sri Lanka, serving seven finalized neural forecasting models through FastAPI and a React dashboard.

## What This App Is

- A dataset-backed inference dashboard.
- The backend lazily loads a selected pre-trained model and its package-specific scalers.
- Every model uses a 96-step lookback, one-step horizon, and the same 20-feature protocol.
- Forecasts are dataset-backed; model weights are never retrained at runtime.

## What This App Is Not (Yet)

- Not a true real-time 2026 national demand monitor.
- Not connected to a live utility/SCADA feed by default.
- Not automatically retraining on new incoming data.

## Quick Start

### Backend

```bash
python -m uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Models

Stable IDs are `cnn`, `lstm`, `transformer`, `cnn_lstm_b`, `cnn_transformer_b`, `cnn_lstm_mc`, and `cnn_transformer_mc`. Runtime artifacts and verified configuration live under `Models/<model_id>/runtime/`. The explicit legacy default is `cnn_lstm_b`.

See [the model integration guide](docs/FINAL_MODEL_INTEGRATION.md) for package layout, compatibility evidence, API payloads, comparison results, and frontend migration guidance.

## API

- `GET /health` — dataset, registry, and lazy-cache readiness.
- `GET /api/models` — structured seven-model registry.
- `POST /api/predict` — selected-model one-step inference.
- `POST /api/compare` — explicit multi-model inference.
- `/models`, `/forecast`, and `/model/metrics` — current frontend compatibility endpoints.

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs` while the backend is running.

## Configuration

The backend supports environment configuration:

- `ALLOWED_ORIGINS` (comma-separated local origins for CORS)
- `DATA_STALE_THRESHOLD_MINUTES` (default: `120`)

The frontend supports:

- `VITE_API_BASE_URL` (default: `/api`)
- `VITE_FORECAST_STEPS` (default: `24`)
- `VITE_FORECAST_PASSES` (retained for the compatibility request)
- `VITE_API_TIMEOUT_MS` (default: `180000`)

## Health Endpoint

`GET /health` returns:

- data and model-registry readiness
- row count
- lazy-loaded model IDs
- oldest/latest dataset timestamp
- data freshness (`data_age_minutes`, `is_data_stale`)
- model compatibility and artifact status

`GET /data/source` returns provider mode and freshness summary used by the frontend mode badge.

## Verification

```bash
python -m pytest -q
cd frontend && npm run lint && npm run build
```

The comparison generator reads saved prediction CSVs without retraining:

```bash
python scripts/generate_final_comparison.py
```
