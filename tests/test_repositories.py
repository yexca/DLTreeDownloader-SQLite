from __future__ import annotations

from pathlib import Path
import sqlite3

from dltree.db import init_schema
from dltree.models import DownloadRequest, ImportRowError, ImportStats, LinkItem, WorkRow
from dltree.repositories import (
    add_import_error,
    create_download,
    create_import,
    finish_import,
    get_active_links,
    get_latest_completed_download_for_work,
    get_latest_download_for_work,
    get_work_by_code,
    refresh_circle_mappings,
    refresh_voice_actor_mappings,
    replace_active_links_if_changed,
    search_by_circle,
    search_by_voice,
    update_download_status,
    upsert_work,
)


def memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def test_schema_can_be_initialized_repeatedly():
    with memory_conn() as conn:
        init_schema(conn)

        version = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()

        assert version["value"] == "1"


def test_upsert_work_inserts_updates_and_keeps_one_work():
    with memory_conn() as conn:
        row = WorkRow(
            work_code="RJ001",
            title="First title",
            voice_actor_raw="A",
            circle_raw="Circle",
            archive_size_raw="10 MB",
            archive_size_bytes=10,
            source_row_number=2,
        )

        work_id, inserted, changed = upsert_work(conn, row, "2026-06-07T00:00:00Z")
        same_id, same_inserted, same_changed = upsert_work(
            conn, row, "2026-06-07T00:01:00Z"
        )
        updated_id, updated_inserted, updated_changed = upsert_work(
            conn,
            WorkRow(work_code="RJ001", title="Updated title"),
            "2026-06-07T00:02:00Z",
        )

        count = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
        record = get_work_by_code(conn, "RJ001")

        assert (work_id, inserted, changed) == (1, True, True)
        assert (same_id, same_inserted, same_changed) == (work_id, False, False)
        assert (updated_id, updated_inserted, updated_changed) == (
            work_id,
            False,
            True,
        )
        assert count == 1
        assert record is not None
        assert record.title == "Updated title"


def test_get_work_by_code_hides_deleted_by_default():
    with memory_conn() as conn:
        work_id, _, _ = upsert_work(
            conn,
            WorkRow(work_code="RJ001", title="Title"),
            "2026-06-07T00:00:00Z",
        )
        conn.execute("UPDATE works SET is_deleted = 1 WHERE id = ?", (work_id,))

        assert get_work_by_code(conn, "RJ001") is None
        assert get_work_by_code(conn, "RJ001", visible_only=False) is not None


def test_refresh_mappings_dedupes_and_replaces_current_work_mappings():
    with memory_conn() as conn:
        work_id, _, _ = upsert_work(
            conn,
            WorkRow(work_code="RJ001", title="Title"),
            "2026-06-07T00:00:00Z",
        )

        refresh_voice_actor_mappings(conn, work_id, ["Alice", "Bob", "Alice"])
        refresh_circle_mappings(conn, work_id, ["Circle A"])
        refresh_voice_actor_mappings(conn, work_id, ["Bob"])
        refresh_circle_mappings(conn, work_id, ["Circle B"])

        voice_names = [
            row["name"]
            for row in conn.execute(
                """
                SELECT va.name
                FROM voice_actors AS va
                JOIN work_voice_actors AS wva ON wva.voice_actor_id = va.id
                WHERE wva.work_id = ?
                """,
                (work_id,),
            ).fetchall()
        ]
        circle_names = [
            row["name"]
            for row in conn.execute(
                """
                SELECT c.name
                FROM circles AS c
                JOIN work_circles AS wc ON wc.circle_id = c.id
                WHERE wc.work_id = ?
                """,
                (work_id,),
            ).fetchall()
        ]

        assert voice_names == ["Bob"]
        assert circle_names == ["Circle B"]


def test_replace_active_links_is_idempotent_and_soft_deletes_changed_links():
    with memory_conn() as conn:
        work_id, _, _ = upsert_work(
            conn,
            WorkRow(work_code="RJ001", title="Title"),
            "2026-06-07T00:00:00Z",
        )
        first_links = [
            LinkItem("C", "a.zip", "https://mega.nz/file/a", 10, 0),
            LinkItem("C", "b.zip", "https://mega.nz/file/b", 20, 1),
        ]
        changed_links = [
            LinkItem("C", "c.zip", "https://mega.nz/file/c", 30, 0),
        ]

        first_changed = replace_active_links_if_changed(
            conn, work_id, first_links, "2026-06-07T00:01:00Z"
        )
        second_changed = replace_active_links_if_changed(
            conn, work_id, first_links, "2026-06-07T00:02:00Z"
        )
        third_changed = replace_active_links_if_changed(
            conn, work_id, changed_links, "2026-06-07T00:03:00Z"
        )

        active_links = get_active_links(conn, work_id)
        deleted_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM download_links
            WHERE work_id = ?
              AND is_deleted = 1
              AND deleted_at = '2026-06-07T00:03:00Z'
            """,
            (work_id,),
        ).fetchone()[0]

        assert first_changed is True
        assert second_changed is False
        assert third_changed is True
        assert [link.file_name for link in active_links] == ["c.zip"]
        assert deleted_count == 2


def test_replace_active_links_empty_new_set_is_not_changed_without_active_links():
    with memory_conn() as conn:
        work_id, _, _ = upsert_work(
            conn,
            WorkRow(work_code="RJ001", title="Title"),
            "2026-06-07T00:00:00Z",
        )

        changed = replace_active_links_if_changed(
            conn, work_id, [], "2026-06-07T00:01:00Z"
        )

        assert changed is False
        assert get_active_links(conn, work_id) == []


def test_import_and_download_records_are_written():
    with memory_conn() as conn:
        work_id, _, _ = upsert_work(
            conn,
            WorkRow(work_code="RJ001", title="Title"),
            "2026-06-07T00:00:00Z",
        )
        import_id = create_import(
            conn, Path("files") / "DL tree 260308.xlsx", "2026-06-07T00:01:00Z"
        )
        add_import_error(
            conn,
            import_id,
            ImportRowError(
                error_type="invalid_mega_json",
                message="Bad JSON",
                row_number=5,
                work_code="RJ001",
                raw_value="{bad",
            ),
            "2026-06-07T00:02:00Z",
        )
        finish_import(
            conn,
            import_id,
            "completed",
            ImportStats(total_rows=1, inserted_works=1, error_count=1),
            "done",
        )
        download_id = create_download(
            conn,
            DownloadRequest(
                work_id=work_id,
                output_dir=Path("downloads") / "RJ001",
                selected_bytes=10,
                free_bytes_before=100,
            ),
        )
        update_download_status(conn, download_id, "completed", 0, "ok")
        latest_download = get_latest_download_for_work(conn, work_id)
        latest_completed = get_latest_completed_download_for_work(conn, work_id)

        import_row = conn.execute("SELECT * FROM imports WHERE id = ?", (import_id,)).fetchone()
        error_row = conn.execute(
            "SELECT * FROM import_errors WHERE import_id = ?", (import_id,)
        ).fetchone()
        download_row = conn.execute(
            "SELECT * FROM downloads WHERE id = ?", (download_id,)
        ).fetchone()

        assert import_row["status"] == "completed"
        assert import_row["total_rows"] == 1
        assert import_row["error_count"] == 1
        assert error_row["error_type"] == "invalid_mega_json"
        assert download_row["status"] == "completed"
        assert download_row["mega_exit_code"] == 0
        assert latest_download is not None
        assert latest_download.status == "completed"
        assert latest_completed is not None
        assert latest_completed.id == download_id


def test_search_by_voice_and_circle_returns_visible_works_with_active_link_stats():
    with memory_conn() as conn:
        work_id, _, _ = upsert_work(
            conn,
            WorkRow(
                work_code="RJ001",
                title="Title",
                voice_actor_raw="Alice",
                circle_raw="Circle A",
                archive_size_raw="30 B",
            ),
            "2026-06-07T00:00:00Z",
        )
        hidden_id, _, _ = upsert_work(
            conn,
            WorkRow(work_code="RJ002", title="Hidden", voice_actor_raw="Alice"),
            "2026-06-07T00:00:00Z",
        )
        refresh_voice_actor_mappings(conn, work_id, ["Alice"])
        refresh_circle_mappings(conn, work_id, ["Circle A"])
        refresh_voice_actor_mappings(conn, hidden_id, ["Alice"])
        replace_active_links_if_changed(
            conn,
            work_id,
            [
                LinkItem("C", "a.zip", "https://mega.nz/file/a", 10, 0),
                LinkItem("C", "b.zip", "https://mega.nz/file/b", 20, 1),
            ],
            "2026-06-07T00:01:00Z",
        )
        conn.execute("UPDATE works SET is_deleted = 1 WHERE id = ?", (hidden_id,))

        voice_results = search_by_voice(conn, "ali", 10)
        circle_results = search_by_circle(conn, "circle", 10)

        assert [result.work_code for result in voice_results] == ["RJ001"]
        assert [result.work_code for result in circle_results] == ["RJ001"]
        assert voice_results[0].active_link_count == 2
        assert voice_results[0].active_link_bytes == 30
