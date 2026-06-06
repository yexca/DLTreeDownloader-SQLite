from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .app import (
    cancel_download,
    doctor,
    execute_download_plan,
    get_info,
    import_workbook,
    initialize,
    prepare_download,
    search_circle,
    search_code,
    search_voice,
)
from .config import DEFAULT_CONFIG_PATH
from .exceptions import DLTError
from .models import DownloadHistory, LinkRecord, WorkRecord, WorkSearchResult
from .sizes import format_size

cli = typer.Typer(no_args_is_help=True, help="DLTreeDownloader command line tool.")
console = Console()


@cli.callback()
def root() -> None:
    """DLTreeDownloader command group."""


@cli.command("init")
def init_command(
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Create default config, database schema, and download directory."""
    result = _call_with_errors(initialize, config)

    table = Table(title="DLTreeDownloader initialized")
    table.add_column("Item")
    table.add_column("Path")
    table.add_column("Status")
    table.add_row(
        "Config",
        str(result.config_path.resolve()),
        "created" if result.config_created else "kept",
    )
    table.add_row("Database", str(result.database_path.resolve()), "ready")
    table.add_row("Downloads", str(result.downloads_path.resolve()), "ready")
    console.print(table)


@cli.command("import")
def import_command(
    xlsx_path: Path = typer.Argument(..., help="Path to the Excel workbook."),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Import an Excel workbook into the local SQLite database."""
    progress_task_id = None

    with Progress(
        TextColumn("[bold blue]Importing[/bold blue]"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        def update_progress(completed: int, total: int | None) -> None:
            nonlocal progress_task_id
            if progress_task_id is None:
                progress_task_id = progress.add_task("import", total=total)
            progress.update(progress_task_id, completed=completed, total=total)

        result = _call_with_errors(
            import_workbook,
            xlsx_path,
            config,
            progress_callback=update_progress,
        )
    stats = result.stats

    table = Table(title="Import completed")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Source", str(result.source_path))
    table.add_row("Rows", str(stats.total_rows))
    table.add_row("Inserted works", str(stats.inserted_works))
    table.add_row("Updated works", str(stats.updated_works))
    table.add_row("Skipped works", str(stats.skipped_works))
    table.add_row("Link sets changed", str(stats.link_sets_changed))
    table.add_row("Errors", str(stats.error_count))
    if result.database_path is not None:
        table.add_row("Database", str(result.database_path))
    if result.error_log_path is not None:
        table.add_row("Error log", str(result.error_log_path.resolve()))
    console.print(table)

    if stats.error_count:
        if result.error_log_path is not None:
            console.print(f"[yellow]Some rows had import errors. Details: {result.error_log_path.resolve()}[/yellow]")
        else:
            console.print("[yellow]Some rows had import errors.[/yellow]")


@cli.command("search-code")
def search_code_command(
    work_code: str = typer.Argument(..., help="Work code to find."),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Find one visible work by exact work code."""
    result = _call_with_errors(search_code, work_code, config)
    _print_search_results("Search result", (result,))


@cli.command("search-voice")
def search_voice_command(
    name: str = typer.Argument(..., help="Voice actor name or partial name."),
    limit: int = typer.Option(50, "--limit", "-n", min=1, help="Maximum rows."),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Search visible works by voice actor."""
    results = _call_with_errors(search_voice, name, limit=limit, config_path=config)
    _print_search_results("Voice search results", results)


@cli.command("search-circle")
def search_circle_command(
    name: str = typer.Argument(..., help="Circle name or partial name."),
    limit: int = typer.Option(50, "--limit", "-n", min=1, help="Maximum rows."),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Search visible works by circle."""
    results = _call_with_errors(search_circle, name, limit=limit, config_path=config)
    _print_search_results("Circle search results", results)


@cli.command("info")
def info_command(
    work_code: str = typer.Argument(..., help="Work code to inspect."),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Show one work and its active links."""
    info = _call_with_errors(get_info, work_code, config)
    _print_work_info(info.work, info.active_links)


@cli.command("doctor")
def doctor_command(
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Check configuration, database, downloads path, and MEGAcmd login."""
    result = _call_with_errors(doctor, config)
    table = Table(title="DLTreeDownloader doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    for check in result.checks:
        table.add_row(check.name, "OK" if check.ok else "Problem", check.message)
    console.print(table)

    if not result.ok:
        raise typer.Exit(4)


@cli.command("download")
def download_command(
    work_code: str = typer.Argument(..., help="Work code to download."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory. Defaults to downloads/<work_code>.",
    ),
    include_par2: bool = typer.Option(
        False,
        "--include-par2",
        help="Include .par2 files.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation.",
    ),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Download active MEGA links for one work."""
    plan = _call_with_errors(
        prepare_download,
        work_code,
        output_dir=output,
        include_par2=include_par2,
        config_path=config,
    )

    _print_download_plan(plan)
    if not yes and not typer.confirm("Start download?"):
        _call_with_errors(cancel_download, plan.download_id, config_path=config)
        console.print("[yellow]Download cancelled.[/yellow]")
        return

    result = _call_with_errors(execute_download_plan, plan, config_path=config)
    console.print(f"[green]{result.message}[/green]")


def _print_search_results(title: str, results: tuple[WorkSearchResult, ...]) -> None:
    table = Table(title=title)
    table.add_column("Code")
    table.add_column("Sale date")
    table.add_column("Title")
    table.add_column("Circle")
    table.add_column("Voice")
    table.add_column("Archive")
    table.add_column("Links", justify="right")
    table.add_column("Link bytes", justify="right")
    for result in results:
        table.add_row(
            result.work_code,
            _display(result.sale_date),
            _display(result.title),
            _display(result.circle_raw),
            _display(result.voice_actor_raw),
            _display(result.archive_size_raw),
            str(result.active_link_count or 0),
            format_size(result.active_link_bytes or 0),
        )
    console.print(table)


def _print_work_info(work: WorkRecord, links: tuple[LinkRecord, ...]) -> None:
    table = Table(title=f"Work {work.work_code}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Code", work.work_code)
    table.add_row("Title", _display(work.title))
    table.add_row("Sale date", _display(work.sale_date))
    table.add_row("Type", _display(work.work_type))
    table.add_row("Tags", _display(work.tags_raw))
    table.add_row("Note", _display(work.note))
    table.add_row("Voice", _display(work.voice_actor_raw))
    table.add_row("Circle", _display(work.circle_raw))
    table.add_row("Archive size", _display(work.archive_size_raw))
    table.add_row("MP3 size", _display(work.mp3_size_raw))
    console.print(table)

    links_table = Table(title="Active links")
    links_table.add_column("#", justify="right")
    links_table.add_column("Group")
    links_table.add_column("File")
    links_table.add_column("Size", justify="right")
    links_table.add_column("par2")
    for index, link in enumerate(links, start=1):
        links_table.add_row(
            str(index),
            link.link_group,
            link.file_name,
            format_size(link.size_bytes),
            "yes" if link.file_name.casefold().endswith(".par2") else "no",
        )
    console.print(links_table)


def _print_download_plan(plan) -> None:
    table = Table(title="Download plan")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Work", plan.work.work_code)
    table.add_row("Title", plan.work.title or "-")
    table.add_row("Output", str(plan.output_dir))
    table.add_row(
        "Files",
        f"{len(plan.selected_links)} selected, {len(plan.excluded_par2_links)} .par2 excluded",
    )
    table.add_row("Selected size", format_size(plan.selected_bytes))
    table.add_row("Safety margin", format_size(plan.margin_bytes))
    table.add_row("Required space", format_size(plan.required_bytes))
    table.add_row("Free space", format_size(plan.free_bytes_before))
    table.add_row("Previous downloads", _format_download_history(plan))
    console.print(table)


def _format_download_history(plan) -> str:
    if plan.latest_completed_download is not None:
        return "Previously completed: " + _format_download_record(plan.latest_completed_download)
    if plan.latest_download is not None:
        return "No completed download. Latest: " + _format_download_record(plan.latest_download)
    return "No previous download records."


def _format_download_record(record: DownloadHistory) -> str:
    return (
        f"{record.status} at {record.requested_at}; "
        f"output={record.output_dir}; "
        f"selected={format_size(record.selected_bytes)}"
    )


def _display(value: object | None) -> str:
    return str(value) if value not in (None, "") else "-"


def _call_with_errors(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except DLTError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(error.exit_code) from error


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
