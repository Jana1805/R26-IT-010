# How the Forecast Works

## Simple explanation

Yes—the selected model's trained `.keras` file is used to generate the forecast.

In the dashboard, you select:

1. A timestamp
2. A model
3. The number of forecast steps

The frontend sends these choices to the backend. The backend finds the selected timestamp in the bundled electricity dataset, prepares the previous 96 chronological records, loads the selected model package, and runs the `.keras` model.

## Forecast flow

```text
Selected timestamp and model
        ↓
Backend finds the timestamp in the dataset
        ↓
Previous 96 records are collected
        ↓
Features are placed in the model's required order
        ↓
The selected model's feature scaler transforms the values
        ↓
The selected .keras model generates a scaled prediction
        ↓
The selected model's target scaler converts it back to kW
        ↓
Forecast is returned to the dashboard
```

## Model selection

Each model ID points to its own package under `Models/`:

- `cnn`
- `lstm`
- `transformer`
- `cnn_lstm_b`
- `cnn_transformer_b`
- `cnn_lstm_mc`
- `cnn_transformer_mc`

For example, selecting `cnn_lstm_b` uses:

```text
Models/cnn_lstm_b/runtime/best_model.keras
Models/cnn_lstm_b/runtime/feat_scaler.pkl
Models/cnn_lstm_b/runtime/target_scaler.pkl
Models/cnn_lstm_b/runtime/production_config.json
```

The backend never silently changes to another model. If the selected model cannot be loaded, it returns an error.

## Timestamp handling

The model needs exactly 96 previous 15-minute records, equivalent to 24 hours of history. These records include weather, calendar information, public-event indicators, Poya-day information, and causal demand-lag features.

The prediction is for the next 15-minute timestamp because every finalized model has:

- Lookback: 96 records
- Horizon: 1 record
- Output: one electricity-demand prediction in kW

The current dashboard forecast is dataset-backed. It can compare a prediction with the known actual demand when the following timestamp exists in the bundled dataset. It is not connected to a live electricity-grid data source.

## Deterministic and MC Dropout models

Deterministic models run the `.keras` model once and return one prediction.

MC Dropout models run the same `.keras` model repeatedly with Dropout active. The backend returns:

- Predictive mean in kW
- Predictive standard deviation in kW
- Calibrated lower and upper bounds when defined by the model configuration

## Model loading

Models are loaded lazily. This means the backend does not load all seven models when it starts. The first request for a model loads and validates its `.keras` file and scalers. The loaded package is then cached for later requests.

No model is retrained or modified during forecasting.
