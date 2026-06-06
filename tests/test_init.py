from __future__ import annotations

import sqlite3

import pytest

from dltree.app import initialize
from dltree.db import check_supported_schema, connect_database
from dltree.exceptions import DatabaseError


def test_initialize_creates_config_database_and_downloads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = initialize()

    assert result.config_created is True
    assert (tmp_path / "env" / "config.toml").exists()
    assert (tmp_path / "env" / "dltree.sqlite3").exists()
    assert (tmp_path / "downloads").is_dir()

    with sqlite3.connect(tmp_path / "env" / "dltree.sqlite3") as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "schema_meta",
            "works",
            "voice_actors",
            "work_voice_actors",
            "circles",
            "work_circles",
            "download_links",
            "imports",
            "import_errors",
            "downloads",
        }.issubset(tables)


def test_initialize_is_idempotent_and_keeps_existing_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    first = initialize()
    first.config_path.write_text(
        first.config_path.read_text(encoding="utf-8") + "\n# user note\n",
        encoding="utf-8",
    )

    second = initialize()

    assert second.config_created is False
    assert "# user note" in second.config_path.read_text(encoding="utf-8")
    assert second.database_path.exists()
    assert second.downloads_path.is_dir()


def test_check_supported_schema_reports_uninitialized_database(tmp_path):
    with connect_database(tmp_path / "empty.sqlite3") as conn:
        with pytest.raises(DatabaseError, match="not initialized"):
            check_supported_schema(conn)
