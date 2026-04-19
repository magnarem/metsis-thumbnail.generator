"""Multiprocessing worker loop."""

from __future__ import annotations

from multiprocessing.queues import Queue
from typing import Any

from .generators import WmsThumbnail
from .models import ThumbnailTask, WorkerResult


def worker_main(
    task_queue: Queue[Any],
    result_queue: Queue[Any],
    wms_projection: str,
    wms_layer: str | None,
    wms_style: str | None,
    wms_zoom: float,
    wms_coastlines: bool,
    wms_extent: list[float] | None,
) -> None:
    """Consume tasks from queue and produce results."""
    generator = WmsThumbnail(
        wms_projection=wms_projection,
        wms_layer=wms_layer,
        wms_style=wms_style,
        wms_zoom=wms_zoom,
        wms_coastlines=wms_coastlines,
        wms_extent=wms_extent,
    )

    while True:
        task = task_queue.get()
        if task is None:
            break

        if not isinstance(task, ThumbnailTask):
            result_queue.put(
                WorkerResult(
                    metadata_identifier="unknown",
                    png_bytes=None,
                    error="Invalid task payload",
                )
            )
            continue

        try:
            png_bytes = generator.generate(task)
            result_queue.put(
                WorkerResult(
                    metadata_identifier=task.metadata_identifier,
                    png_bytes=png_bytes,
                    error=None,
                )
            )
        except Exception as exc:  # noqa: BLE001
            result_queue.put(
                WorkerResult(
                    metadata_identifier=task.metadata_identifier,
                    png_bytes=None,
                    error=str(exc),
                )
            )
