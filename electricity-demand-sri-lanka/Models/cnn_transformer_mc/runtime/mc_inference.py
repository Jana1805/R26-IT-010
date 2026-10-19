import json
import sys
from pathlib import Path

import joblib
import numpy as np
import tensorflow as tf

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from cnn_transformer_custom_layers import PositionalEncoding, TransformerBlock


class CNNTransformerMCDropoutForecaster:
    """Load the deployment bundle and produce deterministic or MC forecasts."""

    def __init__(self, bundle_dir=None):
        self.bundle_dir = Path(bundle_dir or MODULE_DIR)
        with open(self.bundle_dir / "deployment_config.json") as file:
            self.config = json.load(file)

        self.feature_scaler = joblib.load(self.bundle_dir / "feat_scaler.pkl")
        self.target_scaler = joblib.load(self.bundle_dir / "target_scaler.pkl")
        custom_objects = {
            "PositionalEncoding": PositionalEncoding,
            "TransformerBlock": TransformerBlock,
            "LoadForecasting>PositionalEncoding": PositionalEncoding,
            "LoadForecasting>TransformerBlock": TransformerBlock,
        }
        self.model = tf.keras.models.load_model(
            self.bundle_dir / "best_model.keras",
            custom_objects=custom_objects,
            compile=False,
        )

    def prepare_sequence(self, feature_frame):
        """Convert a 96-row feature DataFrame into model input shape (1,96,20)."""
        columns = self.config["features"]
        lookback = int(self.config["lookback"])
        if len(feature_frame) != lookback:
            raise ValueError(f"Expected {lookback} rows, received {len(feature_frame)}.")
        missing = [column for column in columns if column not in feature_frame.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")
        scaled = self.feature_scaler.transform(feature_frame[columns])
        return scaled[np.newaxis, ...].astype(np.float32)

    def deterministic_forecast(self, feature_frame):
        X = self.prepare_sequence(feature_frame)
        scaled = self.model.predict(X, verbose=0)
        return float(self.target_scaler.inverse_transform(scaled)[0, 0])

    def mc_forecast(self, feature_frame, mc_samples=None):
        X = self.prepare_sequence(feature_frame)
        n_samples = int(mc_samples or self.config["mc_samples"])
        predictions = np.stack([
            self.model(X, training=True).numpy()
            for _ in range(n_samples)
        ], axis=0)

        mean_scaled = predictions.mean(axis=0)
        std_scaled = predictions.std(axis=0)
        mean_kW = float(self.target_scaler.inverse_transform(mean_scaled)[0, 0])
        std_kW = float(std_scaled[0, 0] * self.target_scaler.scale_[0])
        q_hat = float(self.config["q_hat_kW"])

        return {
            "forecast_kW": mean_kW,
            "mc_std_kW": std_kW,
            "calibrated_lower_kW": mean_kW - q_hat,
            "calibrated_upper_kW": mean_kW + q_hat,
            "mc_samples": n_samples,
        }
