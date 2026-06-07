from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from typer.testing import CliRunner

from dltree import app as app_module
from dltree.cli import cli
from dltree.filesystem import DiskUsage
from dltree.importer import REQUIRED_HEADERS
from dltree.mega import MegaCheckResult, MegaRunResult


runner = CliRunner()


def write_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(list(REQUIRED_HEADERS))
    rows = [
        {
            "RJcode": "RJ001",
            "标签": "tag",
            "MEGA链接": json.dumps(
                {"C": [{"F": "main.zip", "L": "https://mega.nz/file/main", "S": "100"}]}
            ),
            "销售日期": "2026-06-07",
            "声优": "Alice    Bob",
            "标题": "First title",
            "备注": "note",
            "类型": "Voice",
            "社团": "N&R",
            "档案大小": "100 B",
            "MP3大小": "0 B",
        },
        {
            "RJcode": "ABC-002",
            "MEGA链接": json.dumps(
                {"C": [{"F": "extra.zip", "L": "https://mega.nz/file/extra", "S": "200"}]}
            ),
            "销售日期": "2026-06-06",
            "声优": "Carol",
            "标题": "Second title",
            "社团": "Circle B",
            "档案大小": "200 B",
            "MP3大小": "0 B",
        },
    ]
    for row in rows:
        worksheet.append([row.get(header) for header in REQUIRED_HEADERS])
    workbook.save(path)


def test_cli_init_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    first = runner.invoke(cli, ["init"])
    second = runner.invoke(cli, ["init"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "created" in first.output
    assert "kept" in second.output
    assert (tmp_path / "env" / "config.toml").exists()
    assert (tmp_path / "env" / "dltree.sqlite3").exists()


def test_cli_import_and_search_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workbook_path = tmp_path / "sample.xlsx"
    write_workbook(workbook_path)

    assert runner.invoke(cli, ["init"]).exit_code == 0
    imported = runner.invoke(cli, ["import", str(workbook_path)])
    by_code = runner.invoke(cli, ["search-code", "ABC-002"])
    by_voice = runner.invoke(cli, ["search-voice", "Ali", "--limit", "1"])
    by_circle = runner.invoke(cli, ["search-circle", "N&R"])
    info = runner.invoke(cli, ["info", "RJ001"])
    missing = runner.invoke(cli, ["search-code", "RJ404"])

    assert imported.exit_code == 0
    assert "Rows" in imported.output
    assert "2" in imported.output
    assert by_code.exit_code == 0
    assert "ABC-002" in by_code.output
    assert by_voice.exit_code == 0
    assert "RJ001" in by_voice.output
    assert by_circle.exit_code == 0
    assert "N&R" in by_circle.output
    assert info.exit_code == 0
    assert "main.zip" in info.output
    assert missing.exit_code == 3
    assert "No local work found" in missing.output


def test_cli_import_writes_row_errors_to_logs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workbook_path = tmp_path / "sample_with_errors.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(list(REQUIRED_HEADERS))
    worksheet.append(
        [
            "RJ001" if header == "RJcode" else "{bad" if header == "MEGA链接" else None
            for header in REQUIRED_HEADERS
        ]
    )
    workbook.save(workbook_path)

    assert runner.invoke(cli, ["init"]).exit_code == 0

    result = runner.invoke(cli, ["import", str(workbook_path)])
    logs = list((tmp_path / "logs").glob("import_errors_*.csv"))

    assert result.exit_code == 0
    assert "Error log" in result.output
    assert "Some rows had import errors" in result.output
    assert len(logs) == 1
    assert "invalid_mega_json" in logs[0].read_text(encoding="utf-8-sig")


def test_cli_download_yes_succeeds_with_mock_megacmd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workbook_path = tmp_path / "sample.xlsx"
    write_workbook(workbook_path)
    calls = []

    assert runner.invoke(cli, ["init"]).exit_code == 0
    assert runner.invoke(cli, ["import", str(workbook_path)]).exit_code == 0

    monkeypatch.setattr(app_module, "command_available", lambda executable: True)
    monkeypatch.setattr(app_module, "check_login", lambda executable: MegaCheckResult(True))
    monkeypatch.setattr(
        app_module,
        "get_disk_usage_for_output",
        lambda output_dir: DiskUsage(output_dir, 2 * 1024 * 1024 * 1024),
    )

    def fake_mega_get(mega_get, mega_url, output_dir, output_callback=None):
        calls.append((mega_get, mega_url, output_dir))
        if output_callback is not None:
            output_callback("done\n")
        return MegaRunResult(True, 0, stdout="done")

    monkeypatch.setattr(app_module, "run_mega_get", fake_mega_get)

    result = runner.invoke(cli, ["download", "RJ001", "--yes"])

    assert result.exit_code == 0
    assert "MEGAcmd output" in result.output
    assert "done" in result.output
    assert "Downloaded 1 files" in result.output
    assert [call[1] for call in calls] == ["https://mega.nz/file/main"]


def test_cli_download_plan_reports_previous_completed_download(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workbook_path = tmp_path / "sample.xlsx"
    write_workbook(workbook_path)

    assert runner.invoke(cli, ["init"]).exit_code == 0
    assert runner.invoke(cli, ["import", str(workbook_path)]).exit_code == 0

    monkeypatch.setattr(app_module, "command_available", lambda executable: True)
    monkeypatch.setattr(app_module, "check_login", lambda executable: MegaCheckResult(True))
    monkeypatch.setattr(
        app_module,
        "get_disk_usage_for_output",
        lambda output_dir: DiskUsage(output_dir, 2 * 1024 * 1024 * 1024),
    )
    monkeypatch.setattr(
        app_module,
        "run_mega_get",
        lambda mega_get, mega_url, output_dir, output_callback=None: MegaRunResult(
            True,
            0,
            stdout="done",
        ),
    )

    first = runner.invoke(cli, ["download", "RJ001", "--yes"])
    second = runner.invoke(cli, ["download", "RJ001"], input="n\n")

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "Previously completed" in second.output
    assert "downloads" in second.output


def test_cli_config_error_exits_with_code_2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bad_config = tmp_path / "bad.toml"
    bad_config.write_text("[paths]\ndatabase = 'x.sqlite3'\n", encoding="utf-8")

    result = runner.invoke(cli, ["import", "missing.xlsx", "--config", str(bad_config)])

    assert result.exit_code == 2
    assert "Config error" in result.output
