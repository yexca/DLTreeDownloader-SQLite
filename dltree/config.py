from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

from .exceptions import ConfigError

DEFAULT_CONFIG_PATH = Path("env/config.toml")

DEFAULT_CONFIG_TEXT = """[paths]
database = "env/dltree.sqlite3"
downloads = "downloads"

[download]
safety_margin_percent = 5
safety_margin_min_mb = 512
include_par2_by_default = false

[mega]
mega_get = "mega-get"
mega_whoami = "mega-whoami"
"""


@dataclass(frozen=True)
class PathConfig:
    database: str
    downloads: str


@dataclass(frozen=True)
class DownloadConfig:
    safety_margin_percent: int
    safety_margin_min_mb: int
    include_par2_by_default: bool


@dataclass(frozen=True)
class MegaConfig:
    mega_get: str
    mega_whoami: str


@dataclass(frozen=True)
class Config:
    paths: PathConfig
    download: DownloadConfig
    mega: MegaConfig

    @property
    def database_path(self) -> Path:
        return resolve_user_path(self.paths.database)

    @property
    def downloads_path(self) -> Path:
        return resolve_user_path(self.paths.downloads)


def ensure_default_config(config_path: Path = DEFAULT_CONFIG_PATH) -> bool:
    config_path = config_path.expanduser()
    if config_path.exists():
        return False

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
    return True


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> Config:
    config_path = config_path.expanduser()
    if not config_path.exists():
        raise ConfigError(f"Config error: {config_path} does not exist. Run dltree init.")

    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Config error: invalid TOML in {config_path}: {exc}") from exc

    return parse_config(data, config_path)


def parse_config(data: dict[str, Any], config_path: Path = DEFAULT_CONFIG_PATH) -> Config:
    paths_data = _section(data, "paths", config_path)
    download_data = _section(data, "download", config_path)
    mega_data = _section(data, "mega", config_path)

    paths = PathConfig(
        database=_required_str(paths_data, "database", "paths", config_path),
        downloads=_required_str(paths_data, "downloads", "paths", config_path),
    )
    download = DownloadConfig(
        safety_margin_percent=_required_non_negative_int(
            download_data, "safety_margin_percent", "download", config_path
        ),
        safety_margin_min_mb=_required_non_negative_int(
            download_data, "safety_margin_min_mb", "download", config_path
        ),
        include_par2_by_default=_required_bool(
            download_data, "include_par2_by_default", "download", config_path
        ),
    )
    mega = MegaConfig(
        mega_get=_required_str(mega_data, "mega_get", "mega", config_path),
        mega_whoami=_required_str(mega_data, "mega_whoami", "mega", config_path),
    )
    return Config(paths=paths, download=download, mega=mega)


def resolve_user_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path


def _section(data: dict[str, Any], name: str, config_path: Path) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"Config error: missing [{name}] in {config_path}")
    return value


def _required_str(
    section: dict[str, Any],
    key: str,
    section_name: str,
    config_path: Path,
) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Config error: missing {section_name}.{key} in {config_path}")
    return value


def _required_non_negative_int(
    section: dict[str, Any],
    key: str,
    section_name: str,
    config_path: Path,
) -> int:
    value = section.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ConfigError(
            f"Config error: {section_name}.{key} must be a non-negative integer in {config_path}"
        )
    return value


def _required_bool(
    section: dict[str, Any],
    key: str,
    section_name: str,
    config_path: Path,
) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigError(f"Config error: {section_name}.{key} must be true or false in {config_path}")
    return value
