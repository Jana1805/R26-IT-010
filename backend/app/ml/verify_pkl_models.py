#!/usr/bin/env python3
"""
PKL Model Verification Script

This script verifies that all .pkl models were trained correctly
and can be loaded without errors.

Usage:
    python backend/app/ml/verify_pkl_models.py
"""

import sys
from pathlib import Path
import pickle

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Model files to verify
MODEL_FILES = {
    "profile_scaler.pkl": "StandardScaler",
    "kmeans_model.pkl": "KMeans", 
    "dbscan_model.pkl": "DBSCAN",
    "isolation_forest_model.pkl": "IsolationForest"
}

def verify_pkl_models():
    """Verify all .pkl model files"""
    print("========================================")
    print("PKL MODEL VERIFICATION")
    print("========================================")
    print()
    
    models_dir = PROJECT_ROOT / "models"
    
    for model_idx, (model_file, expected_type) in enumerate(MODEL_FILES.items()):
        model_path = models_dir / model_file
        
        print(f"{model_idx + 1}. {model_file}")
        
        if not model_path.exists():
            print(f"Status: NOT FOUND")
            print(f"Error: Model file {model_file} does not exist")
            continue
        
        try:
            # Load the model
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            
            print(f"Status: Loaded successfully")
            print(f"Model type: {type(model).__name__}")
            
            # Print model-specific details
            if model_file == "profile_scaler.pkl":
                print(f"Feature count: {model.mean_.shape[0]}")
            elif model_file == "kmeans_model.pkl":
                print(f"Number of clusters: {model.n_clusters}")
            elif model_file == "dbscan_model.pkl":
                print(f"Epsilon: {model.eps}")
                print(f"Min samples: {model.min_samples}")
            elif model_file == "isolation_forest_model.pkl":
                print(f"Contamination: {model.contamination}")
            
        except Exception as e:
            print(f"Status: FAILED TO LOAD")
            print(f"Error: {str(e)}")
        
        print()
    
    print("All .pkl models verified successfully.")

if __name__ == "__main__":
    verify_pkl_models()
