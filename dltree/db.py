from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
import sqlite3
from collections.abc import Iterator

from .exceptions import DatabaseError

SUPPORTED_SCHEMA_VERSION = 1


def connect_database(database_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def open_database(database_path: Path) -> Iterator[sqlite3.Connection]:
    conn = connect_database(database_path)
    try:
        yield conn
    finally:
        conn.close()


def init_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with open_database(database_path) as conn:
        init_schema(conn)
        check_supported_schema(conn)


def init_schema(conn: sqlite3.Connection) -> None:
    schema_sql = files("dltree").joinpath("schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()


def get_schema_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.OperationalError as exc:
        raise DatabaseError(
            "Database error: database is not initialized. Run dltree init."
        ) from exc
    if row is None:
        raise DatabaseError("Database error: schema version is missing. Run dltree init.")

    try:
        return int(row["value"])
    except ValueError as exc:
        raise DatabaseError("Database error: schema version is invalid.") from exc


def check_supported_schema(conn: sqlite3.Connection) -> None:
    version = get_schema_version(conn)
    if version > SUPPORTED_SCHEMA_VERSION:
        raise DatabaseError(
            "Database error: this database was created by a newer DLTreeDownloader version."
        )
