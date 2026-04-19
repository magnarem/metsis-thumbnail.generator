"""CLI entry point for Metsis thumbnail generator."""

from __future__ import annotations

from multiprocessing import Process, Queue
from pathlib import Path
from typing import Any

import click
import pysolr

from .config import SolrConnectionConfig, load_app_config, load_solr_config
from .errors import ConfigError, ThumbnailGeneratorError
from .input_handlers import FileInputHandler, SolrInputHandler
from .logging_config import setup_logging
from .models import ThumbnailTask, WorkerResult
from .output_handlers import FailureTracker, ThumbnailOutput
from .worker import worker_main


def _build_solr_client(cfg: SolrConnectionConfig) -> pysolr.Solr:
    auth: tuple[str, str] | None = None
    if cfg.auth_username and cfg.auth_password:
        auth = (cfg.auth_username, cfg.auth_password)
    return pysolr.Solr(cfg.solr_url, always_commit=False, timeout=120, auth=auth)


def _resolve_wms_extent(
    wms_extent: tuple[float, float, float, float] | None,
) -> list[float] | None:
    if wms_extent is None:
        return None
    return [float(value) for value in wms_extent]


def _collect_tasks(
    input_dir: Path | None,
    input_file: Path | None,
    recursive: bool,
    solr_query: str | None,
    solr_client: pysolr.Solr | None,
    num_threads: int,
    page_size: int,
) -> list[ThumbnailTask]:
    if input_dir is not None or input_file is not None:
        file_handler = FileInputHandler(
            input_dir=input_dir,
            input_file=input_file,
            recursive=recursive,
            num_threads=num_threads,
        )
        return list(file_handler.iter_tasks())

    if solr_query is not None and solr_client is not None:
        solr_handler = SolrInputHandler(
            solr_client=solr_client,
            query=solr_query,
            num_threads=num_threads,
            page_size=page_size,
        )
        return list(solr_handler.iter_tasks())

    return []


def _run_workers(
    tasks: list[ThumbnailTask],
    num_processes: int,
    wms_projection: str,
    wms_layer: str | None,
    wms_style: str | None,
    wms_zoom: float,
    wms_coastlines: bool,
    wms_extent: list[float] | None,
) -> list[WorkerResult]:
    task_queue: Queue[Any] = Queue()
    result_queue: Queue[Any] = Queue()

    workers: list[Process] = []
    for _ in range(max(num_processes, 1)):
        process = Process(
            target=worker_main,
            args=(
                task_queue,
                result_queue,
                wms_projection,
                wms_layer,
                wms_style,
                wms_zoom,
                wms_coastlines,
                wms_extent,
            ),
        )
        process.start()
        workers.append(process)

    for task in tasks:
        task_queue.put(task)

    for _ in workers:
        task_queue.put(None)

    results: list[WorkerResult] = []
    for _ in tasks:
        result = result_queue.get()
        if isinstance(result, WorkerResult):
            results.append(result)

    for process in workers:
        process.join()

    return results


@click.command()
@click.option(
    "--config", "config_path", type=click.Path(path_type=Path), default=Path("etc/config.yml")
)
@click.option("--input-dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--input-file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--recursive/--no-recursive", default=True)
@click.option("--solr-query", type=str)
@click.option("--solr-config", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output-path", type=click.Path(file_okay=False, path_type=Path))
@click.option("--batch-size", type=int)
@click.option("--threads", type=int)
@click.option("--processes", type=int)
@click.option("--log-level", default="INFO", show_default=True)
@click.option("--log-file", type=click.Path(path_type=Path))
@click.option("--dry-run", is_flag=True, default=False)
@click.option(
    "--update-solr-thumbnail-url/--no-update-solr-thumbnail-url",
    default=False,
    show_default=True,
    help="Enable Solr atomic updates for thumbnail_url after files are generated.",
)
@click.option("--wms-projection", type=str)
@click.option("--wms-layer", type=str)
@click.option("--wms-style", type=str)
@click.option("--wms-zoom", type=float)
@click.option("--wms-coastlines/--no-wms-coastlines", default=None)
@click.option("--wms-extent", type=float, nargs=4)
def main(
    config_path: Path,
    input_dir: Path | None,
    input_file: Path | None,
    recursive: bool,
    solr_query: str | None,
    solr_config: Path | None,
    output_path: Path | None,
    batch_size: int | None,
    threads: int | None,
    processes: int | None,
    log_level: str,
    log_file: Path | None,
    dry_run: bool,
    update_solr_thumbnail_url: bool,
    wms_projection: str | None,
    wms_layer: str | None,
    wms_style: str | None,
    wms_zoom: float | None,
    wms_coastlines: bool | None,
    wms_extent: tuple[float, float, float, float] | None,
) -> None:
    """Generate thumbnails from folder XML or Solr query results."""
    logger = setup_logging(level=log_level, log_file=str(log_file) if log_file else None)

    file_mode = input_dir is not None or input_file is not None
    if (not file_mode and solr_query is None) or (file_mode and solr_query is not None):
        raise click.UsageError(
            "Use exactly one input mode: --input-dir / --input-file or --solr-query"
        )
    if input_dir is not None and input_file is not None:
        raise click.UsageError("--input-dir and --input-file are mutually exclusive")

    if solr_query and not solr_config:
        raise click.UsageError("--solr-config is required when --solr-query is used")


    if update_solr_thumbnail_url and not solr_config:
        raise click.UsageError(
            "--solr-config is required when --update-solr-thumbnail-url is used"
        )

    try:
        app_config = load_app_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    effective_output_path = output_path or app_config.thumbnail_base_path

    effective_threads = threads or app_config.processing.num_threads
    effective_processes = processes or app_config.processing.num_processes
    effective_batch_size = batch_size or app_config.processing.solr_update_batch_size

    effective_wms_projection = wms_projection or app_config.wms.projection
    effective_wms_layer = wms_layer if wms_layer is not None else app_config.wms.layer
    effective_wms_style = wms_style if wms_style is not None else app_config.wms.style
    effective_wms_zoom = wms_zoom if wms_zoom is not None else app_config.wms.zoom
    effective_wms_coastlines = (
        wms_coastlines if wms_coastlines is not None else app_config.wms.coastlines
    )
    effective_wms_extent = _resolve_wms_extent(wms_extent) or app_config.wms.extent

    source_solr_client: pysolr.Solr | None = None
    target_solr_client: pysolr.Solr | None = None

    if solr_config is not None:
        try:
            solr_cfg = load_solr_config(solr_config)
        except ConfigError as exc:
            raise click.ClickException(str(exc)) from exc

        source_solr_client = _build_solr_client(solr_cfg) if solr_query else None
        target_solr_client = _build_solr_client(solr_cfg) if update_solr_thumbnail_url else None

    if update_solr_thumbnail_url and not app_config.thumbnail_base_url:
        raise click.ClickException(
            "thumbnail_base_url must be set in config when --update-solr-thumbnail-url is used"
        )

    if update_solr_thumbnail_url:
        logger.info("Mode: file-generation-plus-solr-update")
    else:
        logger.info("Mode: file-generation-only (no Solr atomic updates)")
    if input_file is not None:
        logger.info("Scanning single file %s for WMS thumbnail.", input_file)
    elif input_dir is not None:
        logger.info("Scanning %s for WMS thumbnails to generate.", input_dir)
    elif solr_query is not None:
        logger.info("Querying Solr with '%s' for WMS thumbnails to generate.", solr_query)
    tasks = _collect_tasks(
        input_dir=input_dir,
        input_file=input_file,
        recursive=recursive,
        solr_query=solr_query,
        solr_client=source_solr_client,
        num_threads=effective_threads,
        page_size=app_config.processing.solr_page_size,
    )

    logger.info("Loaded %d thumbnail tasks", len(tasks))
    if not tasks:
        logger.warning("No tasks found from selected input")
        return

    if dry_run:
        logger.info("Dry-run enabled, skipping multiprocessing generation")
        return

    results = _run_workers(
        tasks=tasks,
        num_processes=effective_processes,
        wms_projection=effective_wms_projection,
        wms_layer=effective_wms_layer,
        wms_style=effective_wms_style,
        wms_zoom=effective_wms_zoom,
        wms_coastlines=effective_wms_coastlines,
        wms_extent=effective_wms_extent,
    )

    output = ThumbnailOutput(
        base_path=effective_output_path, base_url=app_config.thumbnail_base_url
    )
    failures = FailureTracker()
    solr_updates: list[tuple[str, str]] = []
    task_by_id = {task.metadata_identifier: task for task in tasks}

    for result in results:
        if result.error:
            failures.add(result.metadata_identifier, result.error)
            continue

        if result.png_bytes is None:
            failures.add(result.metadata_identifier, "Empty thumbnail bytes")
            continue

        task = task_by_id.get(result.metadata_identifier)
        if task is None:
            failures.add(result.metadata_identifier, "Task not found during output stage")
            continue

        _, public_url = output.save_thumbnail(
            task=task, png_bytes=result.png_bytes
        )
        if update_solr_thumbnail_url and public_url is not None:
            solr_updates.append((task.metadata_identifier, public_url))

    updated = 0
    if update_solr_thumbnail_url and target_solr_client and solr_updates:
        try:
            updated = output.update_solr_atomic(
                solr_client=target_solr_client,
                update_items=solr_updates,
                batch_size=effective_batch_size,
            )
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(f"Failed to update Solr: {exc}") from exc

    logger.info("Created thumbnails: %d", len(results) - len(failures.failures))
    logger.info("Solr thumbnail_url updates: %d", updated)
    logger.info("Failures: %d", len(failures.failures))
    for failure in failures.failures:
        logger.error(
            "Failed metadata_identifier=%s reason=%s",
            failure["metadata_identifier"],
            failure["reason"],
        )


if __name__ == "__main__":
    try:
        main()
    except ThumbnailGeneratorError as exc:
        raise click.ClickException(str(exc)) from exc
