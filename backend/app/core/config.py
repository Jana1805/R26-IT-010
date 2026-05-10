from pathlib import Path

# This file is at: backend/app/core/config.py
# Project root is 4 levels up: core/ -> app/ -> backend/ -> behaviour-intelligence/
CONFIG_FILE = Path(__file__).resolve()
PROJECT_ROOT = CONFIG_FILE.parent.parent.parent.parent

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
RAW_DATASET_FILENAME = "load_forecasting_dataset_corrected.csv"
BACKEND_PORT = 8001
FRONTEND_URL = "http://localhost:3000"
