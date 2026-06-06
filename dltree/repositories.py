from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import sqlite3

from .link_parser import compute_link_set_hash
from .models import (
    DownloadHistory,
    DownloadRequest,
    ImportErrorRecord,
    ImportRowError,
    ImportStats,
    LinkItem,
    LinkRecord,
    WorkRecord,
    WorkRow,
    WorkSearchResult,
)
from .normalizers import normalize_search_text


def create_import(conn: sqlite3.Connection, source_path: Path, now: str) -> int:
    source_path = Path(source_path)
    source_file_size = source_path.stat().st_size if source_path.exists() else None
    cursor = conn.execute(
        """
        INSERT INTO imports (
            source_path,
            source_file_name,
            source_file_size,
            started_at,
            status
        )
        VALUES (?, ?, ?, ?, 'running')
        """,
        (str(source_path), source_path.name, source_file_size, now),
    )
    return int(cursor.lastrowid)


def finish_import(
    conn: sqlite3.Connection,
    import_id: int,
    status: str,
    stats: ImportStats,
    notes: str | None = None,
) -> None:
    finished_at = _now_from_connection(conn)
    conn.execute(
        """
        UPDATE imports
        SET finished_at = ?,
            status = ?,
            total_rows = ?,
            inserted_works = ?,
            updated_works = ?,
            skipped_works = ?,
            link_sets_changed = ?,
            error_count = ?,
            notes = ?
        WHERE id = ?
        """,
        (
            finished_at,
            status,
            stats.total_rows,
            stats.inserted_works,
            stats.updated_works,
            stats.skipped_works,
            stats.link_sets_changed,
            stats.error_count,
            notes,
            import_id,
        ),
    )


def add_import_error(
    conn: sqlite3.Connection,
    import_id: int,
    error: ImportRowError,
    now: str | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO import_errors (
            import_id,
            row_number,
            work_code,
            error_type,
            message,
            raw_value,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            import_id,
            error.row_number,
            error.work_code,
            error.error_type,
            error.message,
            error.raw_value,
            now or _now_from_connection(conn),
        ),
    )
    return int(cursor.lastrowid)


def list_import_errors(
    conn: sqlite3.Connection,
    import_id: int,
) -> list[ImportErrorRecord]:
    rows = conn.execute(
        """
        SELECT id,
               import_id,
               row_number,
               work_code,
               error_type,
               message,
               raw_value,
               created_at
        FROM import_errors
        WHERE import_id = ?
        ORDER BY id
        """,
        (import_id,),
    ).fetchall()
    return [_import_error_record_from_row(row) for row in rows]


def get_work_by_code(
    conn: sqlite3.Connection,
    work_code: str,
    visible_only: bool = True,
) -> WorkRecord | None:
    sql = """
        SELECT id,
               work_code,
               title,
               tags_raw,
               sale_date,
               voice_actor_raw,
               note,
               work_type,
               circle_raw,
               archive_size_raw,
               archive_size_bytes,
               mp3_size_raw,
               mp3_size_bytes
        FROM works
        WHERE work_code = ?
    """
    params: tuple[object, ...] = (work_code,)
    if visible_only:
        sql += " AND is_deleted = 0"

    row = conn.execute(sql, params).fetchone()
    return _work_record_from_row(row) if row is not None else None


def get_work_search_result_by_code(
    conn: sqlite3.Connection,
    work_code: str,
) -> WorkSearchResult | None:
    row = conn.execute(
        """
        SELECT w.work_code,
               w.title,
               w.sale_date,
               w.circle_raw,
               w.voice_actor_raw,
               w.archive_size_raw,
               COUNT(dl.id) AS active_link_count,
               COALESCE(SUM(dl.size_bytes), 0) AS active_link_bytes
        FROM works AS w
        LEFT JOIN download_links AS dl
               ON dl.work_id = w.id
              AND dl.is_deleted = 0
        WHERE w.work_code = ?
          AND w.is_deleted = 0
        GROUP BY w.id
        """,
        (work_code,),
    ).fetchone()
    return _search_result_from_row(row) if row is not None else None


def upsert_work(conn: sqlite3.Connection, row: WorkRow, now: str) -> tuple[int, bool, bool]:
    existing = conn.execute(
        """
        SELECT id,
               title,
               tags_raw,
               sale_date,
               voice_actor_raw,
               note,
               work_type,
               circle_raw,
               archive_size_raw,
               archive_size_bytes,
               mp3_size_raw,
               mp3_size_bytes,
               source_row_number,
               is_deleted
        FROM works
        WHERE work_code = ?
        """,
        (row.work_code,),
    ).fetchone()

    values = _work_metadata_values(row)
    if existing is None:
        cursor = conn.execute(
            """
            INSERT INTO works (
                work_code,
                title,
                tags_raw,
                sale_date,
                voice_actor_raw,
                note,
                work_type,
                circle_raw,
                archive_size_raw,
                archive_size_bytes,
                mp3_size_raw,
                mp3_size_bytes,
                source_row_number,
                first_imported_at,
                last_seen_at,
                updated_at,
                is_deleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (row.work_code, *values, now, now, now),
        )
        return int(cursor.lastrowid), True, True

    existing_values = tuple(existing[column] for column in _WORK_METADATA_COLUMNS)
    metadata_changed = existing_values != values or bool(existing["is_deleted"])
    work_id = int(existing["id"])

    if metadata_changed:
        conn.execute(
            """
            UPDATE works
            SET title = ?,
                tags_raw = ?,
                sale_date = ?,
                voice_actor_raw = ?,
                note = ?,
                work_type = ?,
                circle_raw = ?,
                archive_size_raw = ?,
                archive_size_bytes = ?,
                mp3_size_raw = ?,
                mp3_size_bytes = ?,
                source_row_number = ?,
                last_seen_at = ?,
                updated_at = ?,
                is_deleted = 0
            WHERE id = ?
            """,
            (*values, now, now, work_id),
        )
    else:
        conn.execute(
            "UPDATE works SET last_seen_at = ?, is_deleted = 0 WHERE id = ?",
            (now, work_id),
        )

    return work_id, False, metadata_changed


def refresh_voice_actor_mappings(
    conn: sqlite3.Connection,
    work_id: int,
    names: Sequence[str],
) -> None:
    conn.execute("DELETE FROM work_voice_actors WHERE work_id = ?", (work_id,))
    for name in _dedupe_names(names):
        voice_actor_id = _get_or_create_named_entity(
            conn,
            table="voice_actors",
            name=name,
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO work_voice_actors (work_id, voice_actor_id)
            VALUES (?, ?)
            """,
            (work_id, voice_actor_id),
        )


def refresh_circle_mappings(
    conn: sqlite3.Connection,
    work_id: int,
    names: Sequence[str],
) -> None:
    conn.execute("DELETE FROM work_circles WHERE work_id = ?", (work_id,))
    for name in _dedupe_names(names):
        circle_id = _get_or_create_named_entity(conn, table="circles", name=name)
        conn.execute(
            """
            INSERT OR IGNORE INTO work_circles (work_id, circle_id)
            VALUES (?, ?)
            """,
            (work_id, circle_id),
        )


def get_active_links(conn: sqlite3.Connection, work_id: int) -> list[LinkRecord]:
    rows = conn.execute(
        """
        SELECT id,
               work_id,
               link_group,
               file_name,
               mega_url,
               size_bytes,
               link_order,
               content_hash,
               is_deleted
        FROM download_links
        WHERE work_id = ?
          AND is_deleted = 0
        ORDER BY link_group, link_order, id
        """,
        (work_id,),
    ).fetchall()
    return [_link_record_from_row(row) for row in rows]


def replace_active_links_if_changed(
    conn: sqlite3.Connection,
    work_id: int,
    links: Sequence[LinkItem],
    now: str,
) -> bool:
    new_hash = compute_link_set_hash(links)
    active_rows = conn.execute(
        """
        SELECT content_hash
        FROM download_links
        WHERE work_id = ?
          AND is_deleted = 0
        ORDER BY link_group, link_order, id
        """,
        (work_id,),
    ).fetchall()

    if not active_rows and not links:
        return False

    if active_rows and all(row["content_hash"] == new_hash for row in active_rows):
        conn.execute(
            """
            UPDATE download_links
            SET last_seen_at = ?
            WHERE work_id = ?
              AND is_deleted = 0
            """,
            (now, work_id),
        )
        return False

    if active_rows:
        conn.execute(
            """
            UPDATE download_links
            SET is_deleted = 1,
                deleted_at = ?
            WHERE work_id = ?
              AND is_deleted = 0
            """,
            (now, work_id),
        )

    for item in links:
        conn.execute(
            """
            INSERT INTO download_links (
                work_id,
                link_group,
                file_name,
                mega_url,
                size_bytes,
                link_order,
                content_hash,
                first_seen_at,
                last_seen_at,
                is_deleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                work_id,
                item.link_group,
                item.file_name,
                item.mega_url,
                item.size_bytes,
                item.link_order,
                new_hash,
                now,
                now,
            ),
        )

    return True


def search_by_voice(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[WorkSearchResult]:
    normalized_query = f"%{normalize_search_text(query)}%"
    rows = conn.execute(
        """
        SELECT w.work_code,
               w.title,
               w.sale_date,
               w.circle_raw,
               w.voice_actor_raw,
               w.archive_size_raw,
               COUNT(dl.id) AS active_link_count,
               COALESCE(SUM(dl.size_bytes), 0) AS active_link_bytes
        FROM works AS w
        JOIN work_voice_actors AS wva ON wva.work_id = w.id
        JOIN voice_actors AS va ON va.id = wva.voice_actor_id
        LEFT JOIN download_links AS dl
               ON dl.work_id = w.id
              AND dl.is_deleted = 0
        WHERE w.is_deleted = 0
          AND va.name_normalized LIKE ?
        GROUP BY w.id
        ORDER BY w.sale_date IS NULL, w.sale_date DESC, w.work_code DESC
        LIMIT ?
        """,
        (normalized_query, limit),
    ).fetchall()
    return [_search_result_from_row(row) for row in rows]


def search_by_circle(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[WorkSearchResult]:
    normalized_query = f"%{normalize_search_text(query)}%"
    rows = conn.execute(
        """
        SELECT w.work_code,
               w.title,
               w.sale_date,
               w.circle_raw,
               w.voice_actor_raw,
               w.archive_size_raw,
               COUNT(dl.id) AS active_link_count,
               COALESCE(SUM(dl.size_bytes), 0) AS active_link_bytes
        FROM works AS w
        JOIN work_circles AS wc ON wc.work_id = w.id
        JOIN circles AS c ON c.id = wc.circle_id
        LEFT JOIN download_links AS dl
               ON dl.work_id = w.id
              AND dl.is_deleted = 0
        WHERE w.is_deleted = 0
          AND c.name_normalized LIKE ?
        GROUP BY w.id
        ORDER BY w.sale_date IS NULL, w.sale_date DESC, w.work_code DESC
        LIMIT ?
        """,
        (normalized_query, limit),
    ).fetchall()
    return [_search_result_from_row(row) for row in rows]


def create_download(conn: sqlite3.Connection, request: DownloadRequest) -> int:
    cursor = conn.execute(
        """
        INSERT INTO downloads (
            work_id,
            requested_at,
            output_dir,
            selected_bytes,
            free_bytes_before,
            status
        )
        VALUES (?, ?, ?, ?, ?, 'planned')
        """,
        (
            request.work_id,
            _now_from_connection(conn),
            str(request.output_dir),
            request.selected_bytes,
            request.free_bytes_before,
        ),
    )
    return int(cursor.lastrowid)


def get_latest_download_for_work(
    conn: sqlite3.Connection,
    work_id: int,
) -> DownloadHistory | None:
    row = conn.execute(
        """
        SELECT id,
               work_id,
               requested_at,
               output_dir,
               selected_bytes,
               status,
               mega_exit_code,
               message
        FROM downloads
        WHERE work_id = ?
        ORDER BY requested_at DESC, id DESC
        LIMIT 1
        """,
        (work_id,),
    ).fetchone()
    return _download_history_from_row(row) if row is not None else None


def get_latest_completed_download_for_work(
    conn: sqlite3.Connection,
    work_id: int,
) -> DownloadHistory | None:
    row = conn.execute(
        """
        SELECT id,
               work_id,
               requested_at,
               output_dir,
               selected_bytes,
               status,
               mega_exit_code,
               message
        FROM downloads
        WHERE work_id = ?
          AND status = 'completed'
        ORDER BY requested_at DESC, id DESC
        LIMIT 1
        """,
        (work_id,),
    ).fetchone()
    return _download_history_from_row(row) if row is not None else None


def update_download_status(
    conn: sqlite3.Connection,
    download_id: int,
    status: str,
    exit_code: int | None = None,
    message: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE downloads
        SET status = ?,
            mega_exit_code = ?,
            message = ?
        WHERE id = ?
        """,
        (status, exit_code, message, download_id),
    )


_WORK_METADATA_COLUMNS = (
    "title",
    "tags_raw",
    "sale_date",
    "voice_actor_raw",
    "note",
    "work_type",
    "circle_raw",
    "archive_size_raw",
    "archive_size_bytes",
    "mp3_size_raw",
    "mp3_size_bytes",
    "source_row_number",
)


def _work_metadata_values(row: WorkRow) -> tuple[object, ...]:
    return tuple(getattr(row, column) for column in _WORK_METADATA_COLUMNS)


def _get_or_create_named_entity(
    conn: sqlite3.Connection,
    *,
    table: str,
    name: str,
) -> int:
    cursor = conn.execute(
        f"""
        INSERT OR IGNORE INTO {table} (name, name_normalized)
        VALUES (?, ?)
        """,
        (name, normalize_search_text(name)),
    )
    if cursor.rowcount:
        return int(cursor.lastrowid)

    row = conn.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise sqlite3.IntegrityError(f"Failed to create {table} record for {name!r}")
    return int(row["id"])


def _dedupe_names(names: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            result.append(name)
    return tuple(result)


def _work_record_from_row(row: sqlite3.Row) -> WorkRecord:
    return WorkRecord(
        id=int(row["id"]),
        work_code=row["work_code"],
        title=row["title"],
        tags_raw=row["tags_raw"],
        sale_date=row["sale_date"],
        voice_actor_raw=row["voice_actor_raw"],
        note=row["note"],
        work_type=row["work_type"],
        circle_raw=row["circle_raw"],
        archive_size_raw=row["archive_size_raw"],
        archive_size_bytes=row["archive_size_bytes"],
        mp3_size_raw=row["mp3_size_raw"],
        mp3_size_bytes=row["mp3_size_bytes"],
    )


def _link_record_from_row(row: sqlite3.Row) -> LinkRecord:
    return LinkRecord(
        id=int(row["id"]),
        work_id=int(row["work_id"]),
        link_group=row["link_group"],
        file_name=row["file_name"],
        mega_url=row["mega_url"],
        size_bytes=int(row["size_bytes"]),
        link_order=int(row["link_order"]),
        content_hash=row["content_hash"],
        is_deleted=bool(row["is_deleted"]),
    )


def _search_result_from_row(row: sqlite3.Row) -> WorkSearchResult:
    return WorkSearchResult(
        work_code=row["work_code"],
        title=row["title"],
        sale_date=row["sale_date"],
        circle_raw=row["circle_raw"],
        voice_actor_raw=row["voice_actor_raw"],
        archive_size_raw=row["archive_size_raw"],
        active_link_count=int(row["active_link_count"]),
        active_link_bytes=int(row["active_link_bytes"]),
    )


def _download_history_from_row(row: sqlite3.Row) -> DownloadHistory:
    return DownloadHistory(
        id=int(row["id"]),
        work_id=int(row["work_id"]),
        requested_at=row["requested_at"],
        output_dir=Path(row["output_dir"]),
        selected_bytes=int(row["selected_bytes"]),
        status=row["status"],
        mega_exit_code=row["mega_exit_code"],
        message=row["message"],
    )


def _import_error_record_from_row(row: sqlite3.Row) -> ImportErrorRecord:
    return ImportErrorRecord(
        id=int(row["id"]),
        import_id=int(row["import_id"]),
        row_number=row["row_number"],
        work_code=row["work_code"],
        error_type=row["error_type"],
        message=row["message"],
        raw_value=row["raw_value"],
        created_at=row["created_at"],
    )


def _now_from_connection(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%SZ', 'now')").fetchone()
    return str(row[0])
