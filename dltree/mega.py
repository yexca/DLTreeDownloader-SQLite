from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import threading

_MEGACMD_OUTPUT_ENCODING = "utf-8"


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
    return resolve_command(executable) is not None


def resolve_command(executable: str) -> str | None:
    executable = executable.strip()
    if not executable:
        return None

    expanded = Path(executable).expanduser()
    if _looks_like_path(executable):
        return _resolve_path_candidate(expanded)

    found = shutil.which(executable)
    if found is not None:
        return found

    if _is_windows():
        for directory in _windows_megacmd_dirs():
            resolved = _resolve_path_candidate(directory / executable)
            if resolved is not None:
                return resolved

    return None


def check_login(mega_whoami: str, timeout_seconds: int = 30) -> MegaCheckResult:
    command = resolve_command(mega_whoami) or mega_whoami
    try:
        completed = subprocess.run(
            _subprocess_args(command),
            check=False,
            capture_output=True,
            text=True,
            encoding=_MEGACMD_OUTPUT_ENCODING,
            errors="replace",
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
    output_callback: Callable[[str], None] | None = None,
) -> MegaRunResult:
    command = resolve_command(mega_get) or mega_get
    if output_callback is not None:
        return _run_mega_get_streaming(
            command,
            mega_url,
            output_dir,
            timeout_seconds,
            output_callback,
        )

    completed = subprocess.run(
        _subprocess_args(command, mega_url, str(output_dir)),
        check=False,
        capture_output=True,
        text=True,
        encoding=_MEGACMD_OUTPUT_ENCODING,
        errors="replace",
        timeout=timeout_seconds,
    )
    return MegaRunResult(
        ok=completed.returncode == 0,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _run_mega_get_streaming(
    command: str,
    mega_url: str,
    output_dir: Path,
    timeout_seconds: int | None,
    output_callback: Callable[[str], None],
) -> MegaRunResult:
    process = subprocess.Popen(
        _subprocess_args(command, mega_url, str(output_dir)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding=_MEGACMD_OUTPUT_ENCODING,
        errors="replace",
        bufsize=1,
    )
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []

    stdout_thread = threading.Thread(
        target=_read_stream,
        args=(process.stdout, stdout_parts, output_callback),
    )
    stderr_thread = threading.Thread(
        target=_read_stream,
        args=(process.stderr, stderr_parts, output_callback),
    )
    stdout_thread.start()
    stderr_thread.start()

    try:
        exit_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        exit_code = process.wait()
        stdout_thread.join()
        stderr_thread.join()
        raise subprocess.TimeoutExpired(
            exc.cmd,
            exc.timeout,
            output="".join(stdout_parts),
            stderr="".join(stderr_parts),
        ) from exc

    stdout_thread.join()
    stderr_thread.join()
    return MegaRunResult(
        ok=exit_code == 0,
        exit_code=exit_code,
        stdout="".join(stdout_parts),
        stderr="".join(stderr_parts),
    )


def _read_stream(
    stream,
    output_parts: list[str],
    output_callback: Callable[[str], None],
) -> None:
    if stream is None:
        return

    with stream:
        while True:
            chunk = stream.read(1)
            if chunk == "":
                break
            output_parts.append(chunk)
            output_callback(chunk)


def _subprocess_args(command: str, *args: str) -> list[str]:
    if _is_windows() and Path(command).suffix.casefold() in {".bat", ".cmd"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "call", command, *args]
    return [command, *args]


def _resolve_path_candidate(path: Path) -> str | None:
    for candidate in _path_candidates(path):
        if candidate.is_file():
            return str(candidate)
    return None


def _path_candidates(path: Path) -> tuple[Path, ...]:
    if path.suffix or not _is_windows():
        return (path,)

    extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
    return tuple(path.with_suffix(extension.lower()) for extension in extensions if extension)


def _windows_megacmd_dirs() -> tuple[Path, ...]:
    values = [
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ]
    paths = [Path(value) / "MEGAcmd" for value in values if value]

    try:
        paths.append(Path.home() / "AppData" / "Local" / "MEGAcmd")
    except RuntimeError:
        pass

    return tuple(dict.fromkeys(paths))


def _looks_like_path(value: str) -> bool:
    return any(separator in value for separator in ("/", "\\")) or Path(value).is_absolute()


def _is_windows() -> bool:
    return os.name == "nt"
