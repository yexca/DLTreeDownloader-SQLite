from __future__ import annotations

import json
import sqlite3

import pytest
from openpyxl import Workbook

from dltree.db import init_schema
from dltree.exceptions import ImportExecutionError
from dltree.importer import REQUIRED_HEADERS, import_excel_workbook
from dltree.repositories import get_active_links


def memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def write_workbook(path, rows, headers=REQUIRED_HEADERS):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(list(headers))
    for row in rows:
        worksheet.append([row.get(header) for header in headers])
    workbook.save(path)


def valid_link(file_name="RJ001.zip", url="https://mega.nz/file/a", size=10):
    return json.dumps(
        {"C": [{"F": file_name, "L": url, "S": str(size)}]},
        ensure_ascii=False,
    )


def test_import_excel_workbook_records_rows_errors_and_is_idempotent(tmp_path):
    workbook_path = tmp_path / "fixture.xlsx"
    write_workbook(
        workbook_path,
        [
            {
                "RJcode": " RJ001 ",
                "标签": "tag",
                "MEGA链接": valid_link(),
                "销售日期": "2026-06-07",
                "声优": "Alice    Bob",
                "标题": "First",
                "备注": "note",
                "类型": "Voice",
                "社团": "Circle A",
                "档案大小": "10 MB",
                "MP3大小": "117 KB",
            },
            {
                "RJcode": " ",
                "标题": "Missing code",
            },
            {
                "RJcode": "RJ002",
                "MEGA链接": "{bad",
                "销售日期": "2026/06/07",
                "声优": "Alice",
                "标题": "Second",
                "社团": "Circle B",
                "档案大小": "bad",
                "MP3大小": "1 MB",
            },
        ],
    )

    with memory_conn() as conn:
        first = import_excel_workbook(conn, workbook_path)
        second = import_excel_workbook(conn, workbook_path)

        works = conn.execute("SELECT work_code FROM works ORDER BY work_code").fetchall()
        active_links = conn.execute(
            "SELECT file_name FROM download_links WHERE is_deleted = 0"
        ).fetchall()
        errors = conn.execute(
            "SELECT error_type FROM import_errors ORDER BY id"
        ).fetchall()

        assert first.stats.total_rows == 3
        assert first.stats.inserted_works == 2
        assert first.stats.link_sets_changed == 1
        assert first.stats.error_count == 4
        assert second.stats.inserted_works == 0
        assert second.stats.skipped_works == 2
        assert [row["work_code"] for row in works] == ["RJ001", "RJ002"]
        assert [row["file_name"] for row in active_links] == ["RJ001.zip"]
        assert [row["error_type"] for row in errors] == [
            "missing_work_code",
            "invalid_sale_date_format",
            "invalid_size",
            "invalid_mega_json",
            "missing_work_code",
            "invalid_sale_date_format",
            "invalid_size",
            "invalid_mega_json",
        ]


def test_import_excel_workbook_soft_deletes_links_when_set_changes(tmp_path):
    first_path = tmp_path / "first.xlsx"
    second_path = tmp_path / "second.xlsx"
    row = {
        "RJcode": "RJ001",
        "MEGA链接": valid_link("first.zip", "https://mega.nz/file/first", 10),
        "标题": "First",
    }
    changed_row = {
        **row,
        "MEGA链接": valid_link("second.zip", "https://mega.nz/file/second", 20),
    }
    write_workbook(first_path, [row])
    write_workbook(second_path, [changed_row])

    with memory_conn() as conn:
        import_excel_workbook(conn, first_path)
        changed = import_excel_workbook(conn, second_path)

        work_id = conn.execute(
            "SELECT id FROM works WHERE work_code = 'RJ001'"
        ).fetchone()["id"]
        deleted_count = conn.execute(
            "SELECT COUNT(*) FROM download_links WHERE is_deleted = 1"
        ).fetchone()[0]

        assert changed.stats.link_sets_changed == 1
        assert [link.file_name for link in get_active_links(conn, work_id)] == [
            "second.zip"
        ]
        assert deleted_count == 1


def test_import_excel_workbook_reports_progress(tmp_path):
    workbook_path = tmp_path / "fixture.xlsx"
    write_workbook(
        workbook_path,
        [
            {"RJcode": "RJ001", "MEGA链接": valid_link("one.zip")},
            {"RJcode": "RJ002", "MEGA链接": valid_link("two.zip")},
        ],
    )
    updates = []

    with memory_conn() as conn:
        import_excel_workbook(
            conn,
            workbook_path,
            progress_callback=lambda completed, total: updates.append((completed, total)),
        )

    assert updates[0] == (0, 2)
    assert updates[-1] == (2, 2)


def test_import_excel_workbook_reports_missing_required_headers(tmp_path):
    workbook_path = tmp_path / "missing_headers.xlsx"
    write_workbook(workbook_path, [], headers=("RJcode", "标题"))

    with memory_conn() as conn:
        with pytest.raises(ImportExecutionError, match="missing required columns"):
            import_excel_workbook(conn, workbook_path)
