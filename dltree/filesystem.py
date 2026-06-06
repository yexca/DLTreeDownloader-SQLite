from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from .exceptions import ConfigError


@dataclass(frozen=True)
class DiskUsage:
    check_path: Path
    free_bytes: int


def nearest_existing_parent(path: Path) -> Path:
    current = path.expanduser()
    if current.exists():
        return current

    parent = current.parent
    while parent != current:
        if parent.exists():
            return parent
        current = parent
        parent = current.parent

    raise ConfigError(f"Config error: no existing parent directory for {path}")


def get_disk_usage_for_output(output_dir: Path) -> DiskUsage:
    check_path = nearest_existing_parent(output_dir)
    usage = shutil.disk_usage(check_path)
    return DiskUsage(check_path=check_path, free_bytes=usage.free)


def resolve_output_dir(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path
