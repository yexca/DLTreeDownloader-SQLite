from __future__ import annotations

import json
from datetime import date, datetime

import pytest

from dltree.link_parser import compute_link_set_hash, parse_mega_links
from dltree.models import LinkItem
from dltree.normalizers import (
    is_iso_sale_date,
    normalize_optional_text,
    normalize_sale_date,
    normalize_search_text,
    normalize_work_code,
    parse_circles,
    parse_voice_actors,
)
from dltree.sizes import format_size, parse_size_bytes


def test_normalize_optional_text_converts_empty_and_null_to_none():
    assert normalize_optional_text(None) is None
    assert normalize_optional_text("") is None
    assert normalize_optional_text(" null ") is None
    assert normalize_optional_text("  A  ") == "A"


def test_normalize_work_code_requires_value():
    assert normalize_work_code(" RJ01548502 ") == "RJ01548502"
    with pytest.raises(ValueError, match="missing_work_code"):
        normalize_work_code(" ")


def test_normalize_search_text_trims_compresses_spaces_and_casefolds():
    assert normalize_search_text("  AbC   DEF\tG  ") == "abc def g"


def test_normalize_sale_date_handles_dates_and_text():
    assert normalize_sale_date(date(2026, 6, 7)) == "2026-06-07"
    assert normalize_sale_date(datetime(2026, 6, 7, 12, 30)) == "2026-06-07"
    assert normalize_sale_date(" 2026-06-07 ") == "2026-06-07"
    assert normalize_sale_date("2026-06-07 00:00:00") == "2026-06-07"
    assert normalize_sale_date("2026/06/07") == "2026/06/07"
    assert is_iso_sale_date("2026-06-07") is True
    assert is_iso_sale_date("2026/06/07") is False


def test_parse_voice_actors_splits_and_dedupes_in_order():
    assert parse_voice_actors("神代そら") == ("神代そら",)
    assert parse_voice_actors("神代そら    海音ミヅチ") == ("神代そら", "海音ミヅチ")
    assert parse_voice_actors("A、B，C,D,A") == ("A", "B", "C", "D")
    assert parse_voice_actors(None) == ()


def test_parse_circles_keeps_the_whole_cell_as_one_name():
    assert parse_circles("N&R") == ("N&R",)
    assert parse_circles("&MORE") == ("&MORE",)
    assert parse_circles(" リリムワークス /【兎月りりむ。公式】 ") == (
        "リリムワークス /【兎月りりむ。公式】",
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0 B", 0),
        ("117 KB", 117 * 1024),
        ("397.64 MB", int(397.64 * 1024 * 1024)),
        ("4.10 GB", int(4.10 * 1024 * 1024 * 1024)),
        ("1 TB", 1024**4),
        ("bad", None),
        (None, None),
    ],
)
def test_parse_size_bytes(value, expected):
    assert parse_size_bytes(value) == expected


def test_format_size():
    assert format_size(0) == "0 B"
    assert format_size(117 * 1024) == "117.00 KB"
    with pytest.raises(ValueError):
        format_size(-1)


def test_parse_mega_links_valid_json_and_multiple_root_groups():
    payload = {
        "C": [{"F": "RJ01548502.zip", "L": "https://mega.nz/file/a", "S": "3249155727"}],
        "D": [{"F": "bonus.par2", "L": "https://mega.nz/file/b", "S": 12}],
    }

    result = parse_mega_links(json.dumps(payload), row_number=2, work_code="RJ01548502")

    assert result.errors == ()
    assert result.links == (
        LinkItem("C", "RJ01548502.zip", "https://mega.nz/file/a", 3249155727, 0),
        LinkItem("D", "bonus.par2", "https://mega.nz/file/b", 12, 0),
    )


def test_parse_mega_links_invalid_json_records_error():
    result = parse_mega_links("{bad", row_number=3, work_code="RJX")

    assert result.links == ()
    assert len(result.errors) == 1
    assert result.errors[0].error_type == "invalid_mega_json"
    assert result.errors[0].row_number == 3
    assert result.errors[0].work_code == "RJX"


def test_parse_mega_links_records_group_and_item_errors_but_keeps_valid_items():
    payload = {
        "C": [
            {"F": "ok.zip", "L": "https://mega.nz/file/ok", "S": "10"},
            {"L": "https://mega.nz/file/missing-name", "S": "10"},
            {"F": "bad-size.zip", "L": "https://mega.nz/file/bad-size", "S": "1.5"},
        ],
        "D": {"F": "not-array"},
    }

    result = parse_mega_links(json.dumps(payload), row_number=4)

    assert result.links == (LinkItem("C", "ok.zip", "https://mega.nz/file/ok", 10, 0),)
    assert [error.error_type for error in result.errors] == [
        "invalid_mega_link_item",
        "invalid_mega_link_item",
        "invalid_mega_group",
    ]


def test_compute_link_set_hash_is_stable_and_order_sensitive():
    first = [
        LinkItem("C", "a.zip", "https://mega.nz/file/a", 1, 0),
        LinkItem("C", "b.zip", "https://mega.nz/file/b", 2, 1),
    ]
    same = [
        LinkItem("C", "a.zip", "https://mega.nz/file/a", 1, 0),
        LinkItem("C", "b.zip", "https://mega.nz/file/b", 2, 1),
    ]
    reordered = [
        LinkItem("C", "b.zip", "https://mega.nz/file/b", 2, 1),
        LinkItem("C", "a.zip", "https://mega.nz/file/a", 1, 0),
    ]

    assert compute_link_set_hash(first) == compute_link_set_hash(same)
    assert compute_link_set_hash(first) != compute_link_set_hash(reordered)
