from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

_MULTI_SPACE_RE = re.compile(r"\s{2,}")
_VOICE_SEPARATOR_RE = re.compile(r"[、，,]")
_WHITESPACE_RE = re.compile(r"\s+")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?$")


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        text = value.date().isoformat()
    elif isinstance(value, date):
        text = value.isoformat()
    else:
        text = str(value)

    text = text.strip()
    if not text or text.casefold() == "null":
        return None
    return text


def normalize_work_code(value: Any) -> str:
    work_code = normalize_optional_text(value)
    if work_code is None:
        raise ValueError("missing_work_code")
    return work_code


def normalize_search_text(value: Any) -> str:
    text = normalize_optional_text(value)
    if text is None:
        return ""
    return _WHITESPACE_RE.sub(" ", text).casefold()


def normalize_sale_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = normalize_optional_text(value)
    if text is None:
        return None
    match = _DATETIME_DATE_PREFIX_RE.match(text)
    if match is not None:
        return match.group(1)
    return text


def is_iso_sale_date(value: str | None) -> bool:
    return value is None or _ISO_DATE_RE.match(value) is not None


def parse_voice_actors(raw: Any) -> tuple[str, ...]:
    text = normalize_optional_text(raw)
    if text is None:
        return ()

    names: list[str] = []
    for space_part in _MULTI_SPACE_RE.split(text):
        for part in _VOICE_SEPARATOR_RE.split(space_part):
            name = normalize_optional_text(part)
            if name is not None:
                names.append(name)
    return _dedupe_preserve_order(names)


def parse_circles(raw: Any) -> tuple[str, ...]:
    text = normalize_optional_text(raw)
    if text is None:
        return ()
    return (text,)


def _dedupe_preserve_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)
