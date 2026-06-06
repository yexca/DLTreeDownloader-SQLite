from __future__ import annotations

from pathlib import Path
import subprocess

from dltree.mega import check_login, run_mega_get


class Completed:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_check_login_calls_mega_whoami_and_reports_logged_in(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Completed(0, stdout="Account: user@example.com")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_login("mega-whoami", timeout_seconds=12)

    assert result.ok is True
    assert result.exit_code == 0
    assert calls == [
        (
            ["mega-whoami"],
            {
                "check": False,
                "capture_output": True,
                "text": True,
                "timeout": 12,
            },
        )
    ]


def test_check_login_reports_logged_out_marker(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: Completed(0, stdout="Not logged in"),
    )

    result = check_login("mega-whoami")

    assert result.ok is False
    assert result.message == "MEGA account is not logged in. Run mega-login manually."


def test_check_login_handles_missing_command(monkeypatch):
    def fake_run(args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_login("missing-mega-whoami")

    assert result.ok is False
    assert result.message == "MEGAcmd command not found: missing-mega-whoami"


def test_check_login_handles_timeout(monkeypatch):
    def fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(args, timeout=3, output="partial", stderr="slow")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_login("mega-whoami", timeout_seconds=3)

    assert result.ok is False
    assert result.stdout == "partial"
    assert result.stderr == "slow"
    assert result.message == "MEGA login check timed out after 3 seconds."


def test_run_mega_get_uses_argument_list_and_returns_result(monkeypatch, tmp_path):
    calls = []
    output_dir = tmp_path / "downloads"

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Completed(0, stdout="done")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_mega_get(
        "mega-get",
        "https://mega.nz/file/item",
        output_dir,
        timeout_seconds=60,
    )

    assert result.ok is True
    assert result.exit_code == 0
    assert result.stdout == "done"
    assert calls == [
        (
            ["mega-get", "https://mega.nz/file/item", str(output_dir)],
            {
                "check": False,
                "capture_output": True,
                "text": True,
                "timeout": 60,
            },
        )
    ]


def test_run_mega_get_returns_failed_result(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: Completed(2, stderr="failed"),
    )

    result = run_mega_get("mega-get", "https://mega.nz/file/item", Path(tmp_path))

    assert result.ok is False
    assert result.exit_code == 2
    assert result.stderr == "failed"
