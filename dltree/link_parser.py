from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Sequence

from .models import ImportRowError, LinkItem, LinkParseResult
from .normalizers import normalize_optional_text

_INTEGER_RE = re.compile(r"^[0-9]+$")


def parse_mega_links(
    raw: Any,
    *,
    row_number: int | None = None,
    work_code: str | None = None,
) -> LinkParseResult:
    text = normalize_optional_text(raw)
    if text is None:
        return LinkParseResult()

    try:
        root = json.loads(text)
    except json.JSONDecodeError:
        return LinkParseResult(
            errors=(
                _error(
                    "invalid_mega_json",
                    "MEGA links must be valid JSON.",
                    row_number,
                    work_code,
                    text,
                ),
            )
        )

    if not isinstance(root, dict):
        return LinkParseResult(
            errors=(
                _error(
                    "invalid_mega_json",
                    "MEGA links JSON root must be an object.",
                    row_number,
                    work_code,
                    text,
                ),
            )
        )

    links: list[LinkItem] = []
    errors: list[ImportRowError] = []
    for group_key, group_items in root.items():
        link_group = str(group_key)
        if not isinstance(group_items, list):
            errors.append(
                _error(
                    "invalid_mega_group",
                    f"MEGA link group {link_group!r} must be an array.",
                    row_number,
                    work_code,
                    json.dumps(group_items, ensure_ascii=False),
                )
            )
            continue

        for link_order, item in enumerate(group_items):
            parsed = _parse_link_item(item, link_group, link_order)
            if isinstance(parsed, LinkItem):
                links.append(parsed)
            else:
                errors.append(
                    _error(
                        "invalid_mega_link_item",
                        parsed,
                        row_number,
                        work_code,
                        json.dumps(item, ensure_ascii=False),
                    )
                )

    return LinkParseResult(links=tuple(links), errors=tuple(errors))


def compute_link_set_hash(links: Sequence[LinkItem]) -> str:
    payload = [
        {
            "link_group": item.link_group,
            "link_order": item.link_order,
            "file_name": item.file_name,
            "mega_url": item.mega_url,
            "size_bytes": item.size_bytes,
        }
        for item in links
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


hash_link_set = compute_link_set_hash


def _parse_link_item(item: Any, link_group: str, link_order: int) -> LinkItem | str:
    if not isinstance(item, dict):
        return "MEGA link item must be an object."

    file_name = normalize_optional_text(item.get("F"))
    mega_url = normalize_optional_text(item.get("L"))
    size_bytes = _parse_non_negative_int(item.get("S"))

    if file_name is None:
        return "MEGA link item is missing F file name."
    if mega_url is None:
        return "MEGA link item is missing L URL."
    if size_bytes is None:
        return "MEGA link item S must be a non-negative integer."

    return LinkItem(
        link_group=link_group,
        file_name=file_name,
        mega_url=mega_url,
        size_bytes=size_bytes,
        link_order=link_order,
    )


def _parse_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        text = value.strip()
        if not _INTEGER_RE.match(text):
            return None
        return int(text)
    return None


def _error(
    error_type: str,
    message: str,
    row_number: int | None,
    work_code: str | None,
    raw_value: str | None,
) -> ImportRowError:
    return ImportRowError(
        error_type=error_type,
        message=message,
        row_number=row_number,
        work_code=work_code,
        raw_value=raw_value,
    )
