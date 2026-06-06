from __future__ import annotations

from .exceptions import ConfigError


def normalize_search_limit(limit: int) -> int:
    if limit < 1:
        raise ConfigError("Config error: search limit must be at least 1.")
    return limit


def require_search_query(query: str, label: str) -> str:
    value = query.strip()
    if not value:
        raise ConfigError(f"Config error: {label} must not be empty.")
    return value
