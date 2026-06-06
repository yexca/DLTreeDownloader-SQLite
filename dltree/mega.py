from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class MegaCheckResult:
    ok: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    message: str | None = None


@dataclass(frozen=True)
class MegaRunResult:
    ok: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""


def command_available(executable: str) -> bool:
    return shutil.which(executable) is not None


def check_login(mega_whoami: str, timeout_seconds: int = 30) -> MegaCheckResult:
    try:
        completed = subprocess.run(
            [mega_whoami],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return MegaCheckResult(False, message=f"MEGAcmd command not found: {mega_whoami}")
    except subprocess.TimeoutExpired as exc:
        return MegaCheckResult(
            False,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            message=f"MEGA login check timed out after {timeout_seconds} seconds.",
        )

    output = f"{completed.stdout}\n{completed.stderr}".casefold()
    logged_out_markers = ("not logged", "not logged in", "not connected", "login")
    ok = completed.returncode == 0 and not any(marker in output for marker in logged_out_markers)
    message = None if ok else "MEGA account is not logged in. Run mega-login manually."
    return MegaCheckResult(
        ok=ok,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        message=message,
    )


def run_mega_get(
    mega_get: str,
    mega_url: str,
    output_dir: Path,
    timeout_seconds: int | None = None,
) -> MegaRunResult:
    completed = subprocess.run(
        [mega_get, mega_url, str(output_dir)],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return MegaRunResult(
        ok=completed.returncode == 0,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
