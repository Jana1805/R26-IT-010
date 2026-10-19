# Final model backend integration

## Runtime design

The API uses `api/core/model_registry.py` as the only production registry for the seven stable IDs. `api/services/model_service.py` loads the selected Keras artifact and that package's scalers on first use, validates their shapes, and caches the package. Startup loads the dataset only.

The explicit backward-compatible default is `cnn_lstm_b`; it is a configuration choice, not an accuracy-based fallback. Invalid or unavailable IDs never fall back to another model.

## Canonical artifact layout

Each `Models/<stable_id>/` directory contains:

- `runtime/`: Keras artifact, package scalers, verified `production_config.json`, and any runtime support files.
- `research/`: original training/evaluation notebook.
- `evaluation/`: original predictions, metrics and figures.

No model, scaler, notebook, CSV, configuration, metric, or figure was discarded. On Windows, `Models` and `models` are the same case-insensitive directory; the contents use the requested stable lowercase IDs.

## Compatibility audit

All Keras files load with TensorFlow/Keras, accept `(None, 96, 20)`, return `(None, 1)`, and produce a finite inverse-scaled prediction. Every feature scaler expects 20 values and every target scaler expects one value. The feature scalers have SHA-256 `fd4e404297a1f9bb...`; target scalers have SHA-256 `e20909898205875c...`. Their fitted parameters and hashes are identical, and the notebooks/configurations confirm the same feature order and 80/10/10 protocol. Each registry entry nevertheless points to its own package files.

| ID | Status | Prediction type | Keras SHA-256 prefix | Prediction CSV |
|---|---|---|---|---|
| `cnn` | compatible | deterministic | `f86fe390b5c76c00` | aligned, 18,817 rows |
| `lstm` | compatible | deterministic | `b9c4ec7cb535fde8` | aligned, 18,817 rows |
| `transformer` | compatible | deterministic | `415fec57945d7f95` | aligned, 18,817 rows |
| `cnn_lstm_b` | compatible | deterministic | `26f21a8957ee05d6` | aligned, 18,817 rows |
| `cnn_transformer_b` | compatible | deterministic | `1329594c91b596d8` | aligned, 18,817 rows |
| `cnn_lstm_mc` | compatible | 100-sample MC mean | `26f21a8957ee05d6` | unavailable; not guessed |
| `cnn_transformer_mc` | compatible | 100-sample MC mean | `1329594c91b596d8` | aligned, 18,817 rows |

Transformer deserialization uses the verified `LoadForecasting` custom-object registrations. MC inference activates Dropout with `training=True`; it refuses models containing Batch Normalization so moving statistics cannot be updated accidentally. The two finalized MC checkpoints contain no Batch Normalization layers. Validation-residual calibrated bounds are returned only for the MC packages whose deployment configurations define `q_hat_kw`.

## Prediction alignment and ranking

Six CSVs have identical timestamp order, row count, test period, actual values and kW units. Metrics were recalculated from those rows; notebook summaries were not copied. `cnn_lstm_mc` has no prediction CSV, so comparison data remains unavailable.

| Rank | Model | MAE kW | RMSE kW | MAPE % | R² |
|---:|---|---:|---:|---:|---:|
| 1 | `cnn_transformer_mc` | 20.4573 | 29.2288 | 0.9674 | 0.9745 |
| 2 | `cnn_lstm_b` | 20.5186 | 29.9782 | 0.9797 | 0.9732 |
| 3 | `lstm` | 30.7177 | 42.8767 | 1.4730 | 0.9451 |
| 4 | `transformer` | 32.6074 | 41.9977 | 1.5427 | 0.9473 |
| 5 | `cnn_transformer_b` | 38.7969 | 46.3825 | 1.7617 | 0.9357 |
| 6 | `cnn` | 39.4558 | 52.3682 | 1.7785 | 0.9181 |

Outputs are under `outputs/final_model_comparison/`: aligned rows, recalculated metrics/ranking, peak metrics, paired moving-block bootstrap results, residual and absolute-error plots, peak-demand plot, and actual-versus-predicted plot. Comparable inference/training cost was not supplied, so the cost table explicitly marks inference time unavailable instead of fabricating it.

No training-history CSV exists in any package. The original training-curve PNGs are preserved, but combined numeric loss curves cannot be generated scientifically.

## API contract

- `GET /api/models`: full registry status, capability and compatibility metadata.
- `POST /api/predict`: one selected-model prediction from exactly 96 ordered rows.
- `POST /api/compare`: explicit multi-model inference with per-model errors.
- `GET /health`: dataset, registry and lazy-cache status.
- Existing `/models`, `/forecast`, and `/model/metrics` contracts remain available for the current frontend.

The standardized input payload contains `model_id`, `forecast_timestamp`, `values`, and optional `feature_names`. Output contains model identity, timestamp, kW prediction, horizon, measured inference time, and uncertainty only when supported. Errors expose stable codes without paths or stack traces.

## Verification

- 12 unit/integration tests passed: registry IDs/status, scaler selection, shape/order/finite checks, missing artifact behavior, deterministic and MC inference, caching, invalid IDs, frontend/API compatibility, alignment and metric calculations.
- 7 real-artifact smoke tests passed: every finalized artifact loaded, matched its declared shape, and produced one finite inverse-scaled prediction.
- Manual API smoke checks passed for `/health`, `/api/models`, `/models`, `/api/predict`, and the legacy `/forecast` adapter.

TensorFlow worker threads keep the Windows pytest process alive after results are printed in this environment; the completed assertions were captured before terminating those idle workers.

## Cleanup and preserved ambiguity

The seven original packages were moved into stable IDs and organized buckets; no required model artifact was deleted. Superseded retraining/screening outputs were removed during final cleanup. Existing top-level `outputs/best_model.keras`, scalers and plots remain preserved for manual provenance review because they are not byte-identical to the final packages and their ownership predates this integration.

## Frontend next step

Replace the frontend's legacy key/value parsing with `GET /api/models`, render only entries with `enabled: true`, send the selected `model_id` to `POST /api/predict` (or `/api/compare`), and show uncertainty controls only when `uncertainty_supported` is true. The current frontend requires no redesign and continues to work through the compatibility routes meanwhile.
