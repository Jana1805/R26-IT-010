import pickle
import os
from xgboost import XGBRegressor
import pandas as pd
import numpy as np

# Create dummy XGBoost model for demonstration
def create_dummy_model():
    # Generate sample data
    np.random.seed(42)
    n_samples = 1000
    n_features = 5  # temperature, rainfall, humidity, wind_speed, public_event

    X = np.random.rand(n_samples, n_features)
    # Scale features to realistic ranges
    X[:, 0] = X[:, 0] * 50  # temperature 0-50
    X[:, 1] = X[:, 1] * 200  # rainfall 0-200
    X[:, 2] = X[:, 2] * 100  # humidity 0-100
    X[:, 3] = X[:, 3] * 50   # wind_speed 0-50
    X[:, 4] = np.random.choice([0, 1], n_samples)  # public_event 0 or 1

    # Generate target (electricity demand) with some correlation
    y = (X[:, 0] * 2 + X[:, 1] * 0.5 + X[:, 2] * 1.5 + X[:, 3] * 0.8 +
         X[:, 4] * 20 + np.random.normal(0, 10, n_samples))

    # Train XGBoost model
    model = XGBRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    # Save model
    model_dir = os.path.join(os.path.dirname(__file__), 'ml_model')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'xgboost_model.pkl')

    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    print(f"Dummy XGBoost model saved to {model_path}")

if __name__ == "__main__":
    create_dummy_model()