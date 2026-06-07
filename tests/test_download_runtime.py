from __future__ import annotations

from pathlib import Path

import pytest

from dltree import app
from dltree.app import (
    calculate_required_bytes,
    doctor,
    execute_download_plan,
    prepare_download,
    select_download_links,
)
from dltree.db import init_database, open_database
from dltree.exceptions import DiskSpaceError, ExternalDependencyError
from dltree.filesystem import DiskUsage
from dltree.mega import MegaCheckResult, MegaRunResult
from dltree.models import LinkItem, WorkRow
from dltree.repositories import get_active_links, replace_active_links_if_changed, upsert_work


def write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[paths]
database = "{(tmp_path / "dltree.sqlite3").as_posix()}"
downloads = "{(tmp_path / "downloads").as_posix()}"

[download]
safety_margin_percent = 5
safety_margin_min_mb = 0
include_par2_by_default = false

[mega]
mega_get = "mega-get"
mega_whoami = "mega-whoami"
""".strip(),
        encoding="utf-8",
    )
    return config_path


def seed_work(config_path: Path, tmp_path: Path) -> None:
    database_path = tmp_path / "dltree.sqlite3"
    init_database(database_path)
    with open_database(database_path) as conn:
        work_id, _, _ = upsert_work(
            conn,
            WorkRow(work_code="RJ001", title="Download me"),
            "2026-06-07T00:00:00Z",
        )
        replace_active_links_if_changed(
            conn,
            work_id,
            [
                LinkItem("C", "main.zip", "https://mega.nz/file/main", 100, 0),
                LinkItem("C", "repair.par2", "https://mega.nz/file/par2", 50, 1),
            ],
            "2026-06-07T00:00:00Z",
        )
        conn.commit()


def seed_par2_only_work(tmp_path: Path) -> None:
    database_path = tmp_path / "dltree.sqlite3"
    init_database(database_path)
    with open_database(database_path) as conn:
        work_id, _, _ = upsert_work(
            conn,
            WorkRow(work_code="RJPAR2", title="Repair files only"),
            "2026-06-07T00:00:00Z",
        )
        replace_active_links_if_changed(
            conn,
            work_id,
            [
                LinkItem("C", "repair.par2", "https://mega.nz/file/par2", 50, 0),
            ],
            "2026-06-07T00:00:00Z",
        )
        conn.commit()


def test_select_download_links_excludes_par2_by_default(tmp_path):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)

    with open_database(tmp_path / "dltree.sqlite3") as conn:
        work = conn.execute("SELECT id FROM works WHERE work_code = 'RJ001'").fetchone()
        links = get_active_links(conn, work["id"])

    selected, excluded = select_download_links(links, include_par2=False)

    assert [link.file_name for link in selected] == ["main.zip"]
    assert [link.file_name for link in excluded] == ["repair.par2"]


def test_select_download_links_includes_par2_when_requested(tmp_path):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)

    with open_database(tmp_path / "dltree.sqlite3") as conn:
        work = conn.execute("SELECT id FROM works WHERE work_code = 'RJ001'").fetchone()
        links = get_active_links(conn, work["id"])

    selected, excluded = select_download_links(links, include_par2=True)

    assert [link.file_name for link in selected] == ["main.zip", "repair.par2"]
    assert excluded == []


def test_calculate_required_bytes_uses_larger_margin(tmp_path):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)

    with open_database(tmp_path / "dltree.sqlite3") as conn:
        work = conn.execute("SELECT id FROM works WHERE work_code = 'RJ001'").fetchone()
        links = get_active_links(conn, work["id"])

    selected_bytes, margin_bytes, required_bytes = calculate_required_bytes(
        links,
        safety_margin_percent=10,
        safety_margin_min_mb=1,
    )

    assert selected_bytes == 150
    assert margin_bytes == 1024 * 1024
    assert required_bytes == selected_bytes + margin_bytes


def test_calculate_required_bytes_uses_percent_margin_when_larger(tmp_path):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)

    with open_database(tmp_path / "dltree.sqlite3") as conn:
        work = conn.execute("SELECT id FROM works WHERE work_code = 'RJ001'").fetchone()
        links = get_active_links(conn, work["id"])

    selected_bytes, margin_bytes, required_bytes = calculate_required_bytes(
        links,
        safety_margin_percent=10,
        safety_margin_min_mb=0,
    )

    assert selected_bytes == 150
    assert margin_bytes == 15
    assert required_bytes == 165


def test_doctor_reports_resolved_megacmd_paths(tmp_path, monkeypatch):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)

    def fake_resolve_command(executable):
        commands = {
            "mega-get": "C:\\Users\\me\\AppData\\Local\\MEGAcmd\\mega-get.exe",
            "mega-whoami": "C:\\Users\\me\\AppData\\Local\\MEGAcmd\\mega-whoami.exe",
        }
        return commands.get(executable)

    monkeypatch.setattr(app, "resolve_command", fake_resolve_command)
    monkeypatch.setattr(app, "check_login", lambda executable: MegaCheckResult(True))

    result = doctor(config_path)

    messages = {check.name: check.message for check in result.checks}
    assert result.ok is True
    assert messages["mega-get"].endswith("MEGAcmd\\mega-get.exe")
    assert messages["mega-whoami"].endswith("MEGAcmd\\mega-whoami.exe")


def test_prepare_download_reports_only_par2_files_without_external_checks(
    tmp_path,
    monkeypatch,
):
    config_path = write_config(tmp_path)
    seed_par2_only_work(tmp_path)
    mega_checked = False

    def fake_command_available(executable):
        nonlocal mega_checked
        mega_checked = True
        return True

    monkeypatch.setattr(app, "command_available", fake_command_available)

    with pytest.raises(app.ConfigError, match="Only \\.par2 files are available"):
        prepare_download("RJPAR2", config_path=config_path)

    assert mega_checked is False


def test_prepare_download_stops_before_login_and_disk_when_megacmd_missing(
    tmp_path,
    monkeypatch,
):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)
    login_called = False
    disk_called = False

    monkeypatch.setattr(app, "command_available", lambda executable: False)

    def fake_login(executable):
        nonlocal login_called
        login_called = True
        return MegaCheckResult(True)

    def fake_disk(output_dir):
        nonlocal disk_called
        disk_called = True
        return DiskUsage(output_dir, 10_000)

    monkeypatch.setattr(app, "check_login", fake_login)
    monkeypatch.setattr(app, "get_disk_usage_for_output", fake_disk)

    with pytest.raises(ExternalDependencyError, match="command not found"):
        prepare_download("RJ001", config_path=config_path)

    assert login_called is False
    assert disk_called is False


def test_prepare_download_stops_before_disk_when_not_logged_in(tmp_path, monkeypatch):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)
    disk_called = False

    monkeypatch.setattr(app, "command_available", lambda executable: True)
    monkeypatch.setattr(
        app,
        "check_login",
        lambda executable: MegaCheckResult(False, message="not logged in"),
    )

    def fake_disk(output_dir):
        nonlocal disk_called
        disk_called = True
        return DiskUsage(output_dir, 10_000)

    monkeypatch.setattr(app, "get_disk_usage_for_output", fake_disk)

    with pytest.raises(ExternalDependencyError, match="not logged in"):
        prepare_download("RJ001", config_path=config_path)

    assert disk_called is False


def test_prepare_download_stops_on_insufficient_disk_before_planned_record(
    tmp_path,
    monkeypatch,
):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)

    monkeypatch.setattr(app, "command_available", lambda executable: True)
    monkeypatch.setattr(app, "check_login", lambda executable: MegaCheckResult(True))
    monkeypatch.setattr(
        app,
        "get_disk_usage_for_output",
        lambda output_dir: DiskUsage(output_dir, 50),
    )

    with pytest.raises(DiskSpaceError, match="Not enough disk space"):
        prepare_download("RJ001", config_path=config_path)

    with open_database(tmp_path / "dltree.sqlite3") as conn:
        count = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]

    assert count == 0


def test_prepare_download_accepts_enough_disk_and_creates_planned_record(
    tmp_path,
    monkeypatch,
):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)

    monkeypatch.setattr(app, "command_available", lambda executable: True)
    monkeypatch.setattr(app, "check_login", lambda executable: MegaCheckResult(True))
    monkeypatch.setattr(
        app,
        "get_disk_usage_for_output",
        lambda output_dir: DiskUsage(output_dir, 10_000),
    )

    plan = prepare_download("RJ001", config_path=config_path)

    assert plan.selected_bytes == 100
    assert plan.free_bytes_before == 10_000
    with open_database(tmp_path / "dltree.sqlite3") as conn:
        row = conn.execute("SELECT status, selected_bytes FROM downloads").fetchone()
    assert row["status"] == "planned"
    assert row["selected_bytes"] == 100


def test_execute_download_plan_calls_mega_get_for_each_selected_url(tmp_path, monkeypatch):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)
    calls = []

    monkeypatch.setattr(app, "command_available", lambda executable: True)
    monkeypatch.setattr(app, "check_login", lambda executable: MegaCheckResult(True))
    monkeypatch.setattr(
        app,
        "get_disk_usage_for_output",
        lambda output_dir: DiskUsage(output_dir, 10_000),
    )

    plan = prepare_download("RJ001", include_par2=True, config_path=config_path)

    def fake_mega_get(mega_get, mega_url, output_dir):
        calls.append((mega_get, mega_url, output_dir))
        return MegaRunResult(True, 0)

    monkeypatch.setattr(app, "run_mega_get", fake_mega_get)

    summary = execute_download_plan(plan, config_path=config_path)

    assert summary.status == "completed"
    assert [call[1] for call in calls] == [
        "https://mega.nz/file/main",
        "https://mega.nz/file/par2",
    ]
    assert plan.output_dir.is_dir()
    with open_database(tmp_path / "dltree.sqlite3") as conn:
        row = conn.execute("SELECT status, mega_exit_code FROM downloads").fetchone()
    assert row["status"] == "completed"
    assert row["mega_exit_code"] == 0


def test_execute_download_plan_records_failure_and_stops_remaining_links(
    tmp_path,
    monkeypatch,
):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)
    calls = []

    monkeypatch.setattr(app, "command_available", lambda executable: True)
    monkeypatch.setattr(app, "check_login", lambda executable: MegaCheckResult(True))
    monkeypatch.setattr(
        app,
        "get_disk_usage_for_output",
        lambda output_dir: DiskUsage(output_dir, 10_000),
    )

    plan = prepare_download("RJ001", include_par2=True, config_path=config_path)

    def fake_mega_get(mega_get, mega_url, output_dir):
        calls.append(mega_url)
        return MegaRunResult(False, 7, stderr="network failed")

    monkeypatch.setattr(app, "run_mega_get", fake_mega_get)

    with pytest.raises(app.DownloadExecutionError, match="exit code 7"):
        execute_download_plan(plan, config_path=config_path)

    assert calls == ["https://mega.nz/file/main"]
    with open_database(tmp_path / "dltree.sqlite3") as conn:
        row = conn.execute("SELECT status, mega_exit_code, message FROM downloads").fetchone()
    assert row["status"] == "failed"
    assert row["mega_exit_code"] == 7
    assert "main.zip" in row["message"]


def test_execute_download_plan_passes_output_callback_to_mega_get(tmp_path, monkeypatch):
    config_path = write_config(tmp_path)
    seed_work(config_path, tmp_path)
    callbacks = []

    monkeypatch.setattr(app, "command_available", lambda executable: True)
    monkeypatch.setattr(app, "check_login", lambda executable: MegaCheckResult(True))
    monkeypatch.setattr(
        app,
        "get_disk_usage_for_output",
        lambda output_dir: DiskUsage(output_dir, 10_000),
    )

    plan = prepare_download("RJ001", config_path=config_path)

    def fake_mega_get(mega_get, mega_url, output_dir, output_callback=None):
        callbacks.append(output_callback)
        if output_callback is not None:
            output_callback("progress\n")
        return MegaRunResult(True, 0, stdout="progress\n")

    monkeypatch.setattr(app, "run_mega_get", fake_mega_get)
    output_chunks = []

    summary = execute_download_plan(
        plan,
        config_path=config_path,
        output_callback=output_chunks.append,
    )

    assert summary.status == "completed"
    assert len(callbacks) == 1
    assert callbacks[0] is not None
    assert output_chunks == ["progress\n"]
