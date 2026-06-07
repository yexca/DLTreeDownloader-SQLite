from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import Config, DEFAULT_CONFIG_PATH, ensure_default_config, load_config
from .db import check_supported_schema, init_database, open_database
from .exceptions import (
    ConfigError,
    DatabaseError,
    DiskSpaceError,
    DownloadExecutionError,
    ExternalDependencyError,
    NotFoundError,
)
from .filesystem import get_disk_usage_for_output, nearest_existing_parent, resolve_output_dir
from .importer import ImportResult, import_excel_workbook
from .mega import check_login, command_available, resolve_command, run_mega_get
from .models import DownloadHistory, DownloadRequest, LinkRecord, WorkRecord
from .repositories import (
    create_download,
    get_active_links,
    get_latest_completed_download_for_work,
    get_latest_download_for_work,
    get_work_by_code,
    get_work_search_result_by_code,
    list_import_errors,
    search_by_circle,
    search_by_voice,
    update_download_status,
)
from .search import normalize_search_limit, require_search_query


@dataclass(frozen=True)
class InitResult:
    config_path: Path
    config_created: bool
    config: Config
    database_path: Path
    downloads_path: Path


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class DoctorResult:
    checks: tuple[DoctorCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


@dataclass(frozen=True)
class DownloadPlan:
    download_id: int
    work: WorkRecord
    selected_links: tuple[LinkRecord, ...]
    excluded_par2_links: tuple[LinkRecord, ...]
    latest_download: DownloadHistory | None
    latest_completed_download: DownloadHistory | None
    output_dir: Path
    selected_bytes: int
    margin_bytes: int
    required_bytes: int
    free_bytes_before: int
    mega_get: str


@dataclass(frozen=True)
class DownloadRunSummary:
    status: str
    downloaded_files: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class WorkInfo:
    work: WorkRecord
    active_links: tuple[LinkRecord, ...]


def initialize(config_path: Path = DEFAULT_CONFIG_PATH) -> InitResult:
    config_created = ensure_default_config(config_path)
    config = load_config(config_path)

    database_path = config.database_path
    downloads_path = config.downloads_path

    init_database(database_path)
    downloads_path.mkdir(parents=True, exist_ok=True)

    return InitResult(
        config_path=config_path,
        config_created=config_created,
        config=config,
        database_path=database_path,
        downloads_path=downloads_path,
    )


def import_workbook(
    xlsx_path: Path,
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    progress_callback=None,
) -> ImportResult:
    config = load_config(config_path)
    database_path = config.database_path

    with open_database(database_path) as conn:
        check_supported_schema(conn)
        result = import_excel_workbook(
            conn,
            xlsx_path,
            database_path=database_path,
            progress_callback=progress_callback,
        )
        if result.stats.error_count == 0:
            return result

        error_log_path = export_import_errors(conn, result.import_id)
        return ImportResult(
            import_id=result.import_id,
            source_path=result.source_path,
            database_path=result.database_path,
            stats=result.stats,
            status=result.status,
            notes=result.notes,
            error_log_path=error_log_path,
        )


def export_import_errors(conn, import_id: int, logs_dir: Path = Path("logs")) -> Path:
    rows = list_import_errors(conn, import_id)
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = logs_dir / f"import_errors_{import_id}_{timestamp}.csv"

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            (
                "id",
                "import_id",
                "row_number",
                "work_code",
                "error_type",
                "message",
                "raw_value",
                "created_at",
            )
        )
        for row in rows:
            writer.writerow(
                (
                    row.id,
                    row.import_id,
                    row.row_number,
                    row.work_code,
                    row.error_type,
                    row.message,
                    row.raw_value,
                    row.created_at,
                )
            )

    return path


def search_code(
    work_code: str,
    config_path: Path = DEFAULT_CONFIG_PATH,
):
    code = require_search_query(work_code, "work_code")
    config = load_config(config_path)
    with open_database(config.database_path) as conn:
        check_supported_schema(conn)
        result = get_work_search_result_by_code(conn, code)
        if result is None:
            raise NotFoundError(
                f"No local work found for {work_code}. Import the latest workbook and try again."
            )
        return result


def search_voice(
    query: str,
    *,
    limit: int = 50,
    config_path: Path = DEFAULT_CONFIG_PATH,
):
    query = require_search_query(query, "voice query")
    limit = normalize_search_limit(limit)
    config = load_config(config_path)
    with open_database(config.database_path) as conn:
        check_supported_schema(conn)
        return tuple(search_by_voice(conn, query, limit))


def search_circle(
    query: str,
    *,
    limit: int = 50,
    config_path: Path = DEFAULT_CONFIG_PATH,
):
    query = require_search_query(query, "circle query")
    limit = normalize_search_limit(limit)
    config = load_config(config_path)
    with open_database(config.database_path) as conn:
        check_supported_schema(conn)
        return tuple(search_by_circle(conn, query, limit))


def get_info(
    work_code: str,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> WorkInfo:
    code = require_search_query(work_code, "work_code")
    config = load_config(config_path)
    with open_database(config.database_path) as conn:
        check_supported_schema(conn)
        work = get_work_by_code(conn, code)
        if work is None:
            raise NotFoundError(
                f"No local work found for {work_code}. Import the latest workbook and try again."
            )
        links = get_active_links(conn, work.id)
        return WorkInfo(work=work, active_links=tuple(links))


def doctor(config_path: Path = DEFAULT_CONFIG_PATH) -> DoctorResult:
    checks: list[DoctorCheck] = []
    try:
        config = load_config(config_path)
    except Exception as exc:
        return DoctorResult((DoctorCheck("Config", False, str(exc)),))

    checks.append(DoctorCheck("Config", True, str(config_path.expanduser())))

    database_path = config.database_path
    if not database_path.exists():
        checks.append(DoctorCheck("Database", False, f"{database_path} does not exist. Run dltree init."))
    else:
        try:
            with open_database(database_path) as conn:
                check_supported_schema(conn)
            checks.append(DoctorCheck("Database", True, str(database_path)))
        except Exception as exc:
            checks.append(DoctorCheck("Database", False, str(exc)))

    try:
        download_parent = nearest_existing_parent(config.downloads_path)
        checks.append(DoctorCheck("Downloads", True, str(download_parent)))
    except Exception as exc:
        checks.append(DoctorCheck("Downloads", False, str(exc)))

    mega_get_command = resolve_command(config.mega.mega_get)
    mega_whoami_command = resolve_command(config.mega.mega_whoami)
    mega_get_ok = mega_get_command is not None
    mega_whoami_ok = mega_whoami_command is not None
    checks.append(
        DoctorCheck(
            "mega-get",
            mega_get_ok,
            mega_get_command if mega_get_command is not None else f"command not found: {config.mega.mega_get}",
        )
    )
    checks.append(
        DoctorCheck(
            "mega-whoami",
            mega_whoami_ok,
            mega_whoami_command if mega_whoami_command is not None else f"command not found: {config.mega.mega_whoami}",
        )
    )

    if mega_whoami_ok:
        login = check_login(config.mega.mega_whoami)
        checks.append(
            DoctorCheck(
                "Login",
                login.ok,
                "logged in" if login.ok else login.message or "not logged in",
            )
        )
    else:
        checks.append(DoctorCheck("Login", False, "mega-whoami is not available"))

    return DoctorResult(tuple(checks))


def prepare_download(
    work_code: str,
    *,
    output_dir: Path | None = None,
    include_par2: bool = False,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> DownloadPlan:
    config = load_config(config_path)
    database_path = config.database_path
    output = resolve_output_dir(output_dir or config.downloads_path / work_code)

    if not database_path.exists():
        raise DatabaseError(f"Database error: {database_path} does not exist. Run dltree init.")

    with open_database(database_path) as conn:
        check_supported_schema(conn)
        work = get_work_by_code(conn, work_code)
        if work is None:
            raise NotFoundError(
                f"No local work found for {work_code}. Import the latest workbook and try again."
            )
        latest_download = get_latest_download_for_work(conn, work.id)
        latest_completed_download = get_latest_completed_download_for_work(conn, work.id)

        active_links = get_active_links(conn, work.id)
        selected_links, excluded_links = select_download_links(
            active_links,
            include_par2=include_par2 or config.download.include_par2_by_default,
        )
        if not selected_links:
            message = f"No downloadable files found for {work_code}."
            if excluded_links:
                message += " Only .par2 files are available; use --include-par2."
            raise ConfigError(message)

        selected_bytes, margin_bytes, required_bytes = calculate_required_bytes(
            selected_links,
            safety_margin_percent=config.download.safety_margin_percent,
            safety_margin_min_mb=config.download.safety_margin_min_mb,
        )

        _ensure_mega_available(config)
        login = check_login(config.mega.mega_whoami)
        if not login.ok:
            raise ExternalDependencyError(login.message or "MEGA account is not logged in.")

        disk = get_disk_usage_for_output(output)
        if disk.free_bytes < required_bytes:
            raise DiskSpaceError(
                "Not enough disk space.\n"
                f"Required: {required_bytes}\n"
                f"Free: {disk.free_bytes}\n"
                f"Output: {output}"
            )

        download_id = create_download(
            conn,
            DownloadRequest(
                work_id=work.id,
                output_dir=output,
                selected_bytes=selected_bytes,
                free_bytes_before=disk.free_bytes,
            ),
        )
        conn.commit()

    return DownloadPlan(
        download_id=download_id,
        work=work,
        selected_links=tuple(selected_links),
        excluded_par2_links=tuple(excluded_links),
        latest_download=latest_download,
        latest_completed_download=latest_completed_download,
        output_dir=output,
        selected_bytes=selected_bytes,
        margin_bytes=margin_bytes,
        required_bytes=required_bytes,
        free_bytes_before=disk.free_bytes,
        mega_get=config.mega.mega_get,
    )


def cancel_download(
    download_id: int,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> None:
    config = load_config(config_path)
    with open_database(config.database_path) as conn:
        check_supported_schema(conn)
        update_download_status(conn, download_id, "blocked", None, "cancelled by user")
        conn.commit()


def execute_download_plan(
    plan: DownloadPlan,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    output_callback: Callable[[str], None] | None = None,
) -> DownloadRunSummary:
    config = load_config(config_path)
    downloaded_files: list[str] = []
    plan.output_dir.mkdir(parents=True, exist_ok=True)

    for index, link in enumerate(plan.selected_links, start=1):
        try:
            if output_callback is None:
                result = run_mega_get(plan.mega_get, link.mega_url, plan.output_dir)
            else:
                result = run_mega_get(
                    plan.mega_get,
                    link.mega_url,
                    plan.output_dir,
                    output_callback=output_callback,
                )
        except Exception as exc:
            message = f"mega-get failed for {link.file_name}: {exc}"
            _finish_download(config, plan.download_id, "failed", None, message)
            raise DownloadExecutionError(message) from exc

        if not result.ok:
            message = _failed_message(link.file_name, index, result.exit_code, result.stderr)
            _finish_download(config, plan.download_id, "failed", result.exit_code, message)
            raise DownloadExecutionError(message)

        downloaded_files.append(link.file_name)

    message = (
        f"Downloaded {len(downloaded_files)} files. "
        f"selected={plan.selected_bytes} free_before={plan.free_bytes_before}"
    )
    _finish_download(config, plan.download_id, "completed", 0, message)
    return DownloadRunSummary(
        status="completed",
        downloaded_files=tuple(downloaded_files),
        message=message,
    )


def select_download_links(
    links: Sequence[LinkRecord],
    include_par2: bool,
) -> tuple[list[LinkRecord], list[LinkRecord]]:
    selected: list[LinkRecord] = []
    excluded: list[LinkRecord] = []
    for link in links:
        if link.file_name.casefold().endswith(".par2") and not include_par2:
            excluded.append(link)
        else:
            selected.append(link)
    return selected, excluded


def calculate_required_bytes(
    selected_links: Sequence[LinkRecord],
    *,
    safety_margin_percent: int,
    safety_margin_min_mb: int,
) -> tuple[int, int, int]:
    selected_bytes = sum(link.size_bytes for link in selected_links)
    margin_bytes = max(
        int(selected_bytes * safety_margin_percent / 100),
        safety_margin_min_mb * 1024 * 1024,
    )
    return selected_bytes, margin_bytes, selected_bytes + margin_bytes


def _ensure_mega_available(config: Config) -> None:
    for executable in (config.mega.mega_get, config.mega.mega_whoami):
        if not command_available(executable):
            raise ExternalDependencyError(
                f"MEGAcmd command not found: {executable}\n"
                f"Install MEGAcmd or set the path in {DEFAULT_CONFIG_PATH}."
            )


def _finish_download(
    config: Config,
    download_id: int,
    status: str,
    exit_code: int | None,
    message: str,
) -> None:
    with open_database(config.database_path) as conn:
        check_supported_schema(conn)
        update_download_status(conn, download_id, status, exit_code, _truncate(message, 2200))
        conn.commit()


def _failed_message(file_name: str, order: int, exit_code: int, stderr: str) -> str:
    return (
        f"mega-get failed for {file_name} at item {order} with exit code {exit_code}. "
        f"stderr={_truncate(stderr, 1000)}"
    )


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "..."
