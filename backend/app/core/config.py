from pathlib import Path


def find_project_root() -> Path:
    """Walk up from this file's location until a directory containing a 'data' folder is found."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "data").is_dir():
            return parent
    raise RuntimeError("Could not find project root: no 'data' directory found in any parent path")


PROJECT_ROOT = find_project_root()
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
RAW_DATASET_FILENAME = "load_forecasting_dataset_corrected.csv"
BACKEND_PORT = 8001
FRONTEND_URL = "http://localhost:3000"
