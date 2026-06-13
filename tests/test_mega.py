from __future__ import annotations

from pathlib import Path
import io
import subprocess

from dltree import mega as mega_module
from dltree.mega import check_login, command_available, resolve_command, run_mega_get


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

    monkeypatch.setattr(mega_module, "resolve_command", lambda executable: None)
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
                "encoding": "utf-8",
                "errors": "replace",
                "timeout": 12,
            },
        )
    ]


def test_command_available_resolves_path_from_shutil_which(monkeypatch):
    monkeypatch.setattr(
        mega_module.shutil,
        "which",
        lambda executable: "C:\\Tools\\mega-whoami.exe" if executable == "mega-whoami" else None,
    )

    assert command_available("mega-whoami") is True
    assert resolve_command("mega-whoami") == "C:\\Tools\\mega-whoami.exe"


def test_resolve_command_finds_windows_megacmd_install_dir(tmp_path, monkeypatch):
    install_dir = tmp_path / "MEGAcmd"
    install_dir.mkdir()
    executable = install_dir / "mega-whoami.exe"
    executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(mega_module, "_is_windows", lambda: True)
    monkeypatch.setattr(mega_module.shutil, "which", lambda executable: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)

    assert resolve_command("mega-whoami") == str(executable)


def test_check_login_uses_resolved_command(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Completed(0, stdout="Account: user@example.com")

    monkeypatch.setattr(mega_module, "resolve_command", lambda executable: "C:\\Tools\\mega-whoami.exe")
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_login("mega-whoami")

    assert result.ok is True
    assert calls == [["C:\\Tools\\mega-whoami.exe"]]


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

    monkeypatch.setattr(mega_module, "resolve_command", lambda executable: None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_mega_get(
        "mega-get",
        "https://mega.nz/file/item",
        output_dir,
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
                "encoding": "utf-8",
                "errors": "replace",
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


def test_run_mega_get_streams_process_output(monkeypatch, tmp_path):
    calls = []
    output_chunks = []

    class FakeProcess:
        def __init__(self, args, **kwargs):
            calls.append((args, kwargs))
            self.stdout = io.StringIO("downloading\r100%\n")
            self.stderr = io.StringIO("warning\n")

        def wait(self):
            return 0

    monkeypatch.setattr(mega_module, "resolve_command", lambda executable: None)
    monkeypatch.setattr(subprocess, "Popen", FakeProcess)

    result = run_mega_get(
        "mega-get",
        "https://mega.nz/file/item",
        tmp_path,
        output_callback=output_chunks.append,
    )

    assert result.ok is True
    assert result.exit_code == 0
    assert result.stdout == "downloading\r100%\n"
    assert result.stderr == "warning\n"
    streamed_output = "".join(output_chunks)
    assert "downloading\r100%\n" in streamed_output
    assert "warning\n" in streamed_output
    assert calls == [
        (
            ["mega-get", "https://mega.nz/file/item", str(tmp_path)],
            {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
                "bufsize": 1,
            },
        )
    ]
