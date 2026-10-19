"""Sanitization and safe conversion helpers."""

from typing import Any


def safe_float(val: Any, fallback: float = 0.0) -> float:
    """Convert to float; fallback for invalid, NaN, or infinite values."""
    try:
        f = float(val)
        if f != f or f == float("inf") or f == float("-inf"):
            return fallback
        return f
    except (ValueError, TypeError):
        return fallback


def sanitize(obj: Any) -> Any:
    """Recursively replace NaN/Inf floats with None for JSON safety."""
    if isinstance(obj, float):
        return None if (obj != obj or obj == float("inf") or obj == float("-inf")) else obj
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


def round_float(val: float, decimals: int = 2) -> float:
    """Round a float with safe fallback behavior."""
    return round(safe_float(val), decimals)
