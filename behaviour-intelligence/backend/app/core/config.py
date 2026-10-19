from pathlib import Path

# This file is at: backend/app/core/config.py
# Project root is 4 levels up: core/ -> app/ -> backend/ -> behaviour-intelligence/
CONFIG_FILE = Path(__file__).resolve()
PROJECT_ROOT = CONFIG_FILE.parent.parent.parent.parent

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
RAW_DATASET_FILENAME = "synthetic_realistic_load.csv"
BACKEND_PORT = 8001
FRONTEND_URL = "http://localhost:3000"

# Hyperparameter tuning evidence written by notebooks/07_hyperparameter_tuning.ipynb
# (workspace root, next to behaviour-intelligence/). Read-only for the API.
THESIS_EVIDENCE_DIR = PROJECT_ROOT.parent / "thesis_evidence"
TUNING_TABLES_DIR = THESIS_EVIDENCE_DIR / "tables_v2"
TUNING_FIGURES_DIR = THESIS_EVIDENCE_DIR / "figures_v2"

# ── Login (home-login branch) ─────────────────────────────────────────────────
# Safety switch: set the environment variable AUTH_ENABLED=false before starting
# the backend to turn login off (the home page stays, "Open dashboard" goes
# straight in). Default: login is on.
import os

AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "true").strip().lower() not in ("false", "0", "no", "off")
USERS_DB_PATH = PROJECT_ROOT / "backend" / "users.db"          # gitignored
AUTH_SECRET_PATH = PROJECT_ROOT / "backend" / ".auth_secret"   # gitignored, created on first start
SESSION_HOURS = 8
