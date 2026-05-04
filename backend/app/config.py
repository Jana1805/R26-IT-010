from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    app_name = os.getenv("APP_NAME", "AI Electricity Scenario Analysis API")
    app_version = os.getenv("APP_VERSION", "1.0.0")
    debug = _get_bool("DEBUG", True)

    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = _get_int("API_PORT", 8000)
    allowed_origins = _get_list(
        "ALLOWED_ORIGINS",
        ["http://localhost:5173", "http://127.0.0.1:5173"],
    )

    mongo_url = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "electricity_demand_db")
    db_connect_on_startup = _get_bool("DB_CONNECT_ON_STARTUP", True)
    db_server_selection_timeout_ms = _get_int("DB_SERVER_SELECTION_TIMEOUT_MS", 10000)

    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-pro")


@lru_cache
def get_settings() -> Settings:
    return Settings()
