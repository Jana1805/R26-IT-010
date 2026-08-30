"""Shared API runtime state and dependency guards."""

from typing import Any

from fastapi import HTTPException

# Support multiple models keyed by name
RAW_DF: Any = None
LOAD_ERRORS: dict[str, list[str]] = {}


def set_data(raw_df: Any, load_errors: dict[str, list[str]] | None = None) -> None:
    global RAW_DF, LOAD_ERRORS
    RAW_DF = raw_df
    LOAD_ERRORS = load_errors or {}


def require_data() -> None:
    """Ensure dataset is loaded before data-backed endpoints."""
    if RAW_DF is None or len(RAW_DF) == 0:
        raise HTTPException(503, "Dataset not loaded. Check DATA_PATH.")
