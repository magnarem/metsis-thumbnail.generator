"""Output handling: filesystem writes and Solr atomic updates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import List, Optional, Tuple

import pysolr

from .deterministic_path import build_thumbnail_public_url
from .models import ThumbnailTask
from .thumbnail_path_api import (
    build_thumbnail_relative_path,
    metadata_identifier_to_solr_id,
)

logger = logging.getLogger("metsis_thumbnail_generator.output")


@dataclass
class FailureTracker:
    """Track failed metadata identifiers with error messages."""

    failures: list[dict[str, str]] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)

    def add(self, metadata_identifier: str, reason: str) -> None:
        with self._lock:
            self.failures.append(
                {
                    "metadata_identifier": metadata_identifier,
                    "reason": reason,
                }
            )


class ThumbnailOutput:
    """Write thumbnails to disk and submit Solr updates."""

    def __init__(self, base_path: Path, base_url: Optional[str]) -> None:
        self.base_path = base_path
        self.base_url = base_url.rstrip("/") if base_url else None

    def resolve_storage_path(self, task: ThumbnailTask) -> Path:
        relative_path = build_thumbnail_relative_path(
            metadata_identifier=task.metadata_identifier,
            start_date=task.start_date,
            wms_url=task.wms_url,
        )
        return self.base_path / relative_path

    def save_thumbnail(
        self, task: ThumbnailTask, png_bytes: bytes
    ) -> Tuple[Path, Optional[str]]:
        destination = self.resolve_storage_path(task)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(png_bytes)
        relative_path = destination.relative_to(self.base_path)

        public_url = None
        if self.base_url:
            public_url = build_thumbnail_public_url(self.base_url, relative_path)

        logger.debug(
            "Saved thumbnail metadata_identifier=%s solr_id=%s wms_url=%s relative_path=%s path=%s public_url=%s",
            task.metadata_identifier,
            metadata_identifier_to_solr_id(task.metadata_identifier),
            task.wms_url,
            relative_path,
            destination,
            public_url,
        )

        return destination, public_url

    @staticmethod
    def _to_atomic_update(metadata_identifier: str, thumbnail_url: str) -> dict[str, object]:
        return {
            "id": metadata_identifier_to_solr_id(metadata_identifier),
            "thumbnail_url": {"set": thumbnail_url},
        }

    def update_solr_atomic(
        self,
        solr_client: pysolr.Solr,
        update_items: List[Tuple[str, str]],
        batch_size: int,
    ) -> int:
        updated = 0
        batch: list[dict[str, object]] = []

        for metadata_identifier, thumbnail_url in update_items:
            batch.append(self._to_atomic_update(metadata_identifier, thumbnail_url))
            if len(batch) >= batch_size:
                solr_client.add(batch, commit=False)
                updated += len(batch)
                batch = []

        if batch:
            solr_client.add(batch, commit=False)
            updated += len(batch)

        if updated > 0:
            solr_client.commit()

        return updated
