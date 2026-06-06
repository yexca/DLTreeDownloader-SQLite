from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any

from .normalizers import normalize_optional_text

_SIZE_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB|TB)$", re.IGNORECASE)
_UNIT_FACTORS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
    "TB": 1024**4,
}


def parse_size_bytes(value: Any) -> int | None:
    text = normalize_optional_text(value)
    if text is None:
        return None

    match = _SIZE_RE.match(text)
    if match is None:
        return None

    number_text, unit_text = match.groups()
    try:
        number = Decimal(number_text)
    except InvalidOperation:
        return None

    factor = _UNIT_FACTORS[unit_text.upper()]
    size = number * factor
    if size < 0:
        return None
    return int(size)


def format_size(size_bytes: int) -> str:
    if size_bytes < 0:
        raise ValueError("size_bytes must be non-negative")

    value = Decimal(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        factor = Decimal(_UNIT_FACTORS[unit])
        next_factor = factor * 1024
        if unit == "TB" or value < next_factor:
            if unit == "B":
                return f"{size_bytes} B"
            display = value / factor
            return f"{display.quantize(Decimal('0.01'))} {unit}"
    return f"{size_bytes} B"


parse_size = parse_size_bytes
