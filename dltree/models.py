from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class WorkRow:
    work_code: str
    title: str | None = None
    tags_raw: str | None = None
    sale_date: str | None = None
    voice_actor_raw: str | None = None
    voice_actor_names: tuple[str, ...] = ()
    note: str | None = None
    work_type: str | None = None
    circle_raw: str | None = None
    circle_names: tuple[str, ...] = ()
    archive_size_raw: str | None = None
    archive_size_bytes: int | None = None
    mp3_size_raw: str | None = None
    mp3_size_bytes: int | None = None
    source_row_number: int | None = None


@dataclass(frozen=True)
class LinkItem:
    link_group: str
    file_name: str
    mega_url: str
    size_bytes: int
    link_order: int


@dataclass
class ImportStats:
    total_rows: int = 0
    inserted_works: int = 0
    updated_works: int = 0
    skipped_works: int = 0
    link_sets_changed: int = 0
    error_count: int = 0


@dataclass(frozen=True)
class ImportRowError:
    error_type: str
    message: str
    row_number: int | None = None
    work_code: str | None = None
    raw_value: str | None = None


@dataclass(frozen=True)
class ImportErrorRecord:
    id: int
    import_id: int
    row_number: int | None
    work_code: str | None
    error_type: str
    message: str
    raw_value: str | None
    created_at: str


@dataclass(frozen=True)
class LinkParseResult:
    links: tuple[LinkItem, ...] = ()
    errors: tuple[ImportRowError, ...] = ()


@dataclass(frozen=True)
class WorkRecord:
    id: int
    work_code: str
    title: str | None
    tags_raw: str | None = None
    sale_date: str | None = None
    voice_actor_raw: str | None = None
    note: str | None = None
    work_type: str | None = None
    circle_raw: str | None = None
    archive_size_raw: str | None = None
    archive_size_bytes: int | None = None
    mp3_size_raw: str | None = None
    mp3_size_bytes: int | None = None


@dataclass(frozen=True)
class LinkRecord:
    id: int
    work_id: int
    link_group: str
    file_name: str
    mega_url: str
    size_bytes: int
    link_order: int
    content_hash: str
    is_deleted: bool = False


@dataclass(frozen=True)
class WorkSearchResult:
    work_code: str
    title: str | None
    sale_date: str | None = None
    circle_raw: str | None = None
    voice_actor_raw: str | None = None
    archive_size_raw: str | None = None
    active_link_count: int | None = None
    active_link_bytes: int | None = None


@dataclass(frozen=True)
class DownloadRequest:
    work_id: int
    output_dir: Path
    selected_bytes: int
    free_bytes_before: int | None = None


@dataclass(frozen=True)
class DownloadHistory:
    id: int
    work_id: int
    requested_at: str
    output_dir: Path
    selected_bytes: int
    status: str
    mega_exit_code: int | None = None
    message: str | None = None


@dataclass(frozen=True)
class DownloadResult:
    status: str
    exit_code: int | None = None
    message: str | None = None
    downloaded_files: tuple[str, ...] = field(default_factory=tuple)
