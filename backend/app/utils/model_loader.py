import pickle
import os
from xgboost import XGBRegressor
import pandas as pd
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_model", "xgboost_model.pkl")

model = None

def load_model():
    global model
    if model is None:
        try:
            with open(MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            print("ML model loaded successfully")
        except FileNotFoundError:
            print(f"Model file not found at {MODEL_PATH}")
            # For demo purposes, create a simple model
            create_dummy_model()
        except Exception as e:
            print(f"Error loading model: {e}")
            create_dummy_model()
    return model

def create_dummy_model():
    global model
    # Create a dummy XGBoost model for demonstration
    # In real scenario, this would be your trained model
    from sklearn.datasets import make_regression
    X, y = make_regression(n_samples=1000, n_features=5, noise=0.1, random_state=42)
    model = XGBRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Save the dummy model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    print("Dummy model created and saved")

def predict_demand(features: dict) -> float:
    model = load_model()
    # Convert features to DataFrame
    df = pd.DataFrame([features])
    prediction = model.predict(df)[0]
    return float(prediction)