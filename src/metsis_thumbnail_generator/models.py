"""Shared data models used across modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ThumbnailTask:
    """Single thumbnail generation work unit."""

    metadata_identifier: str
    start_date: Optional[str]
    wms_url: Optional[str]


@dataclass
class WorkerResult:
    """Result from a worker process."""

    metadata_identifier: str
    png_bytes: Optional[bytes]
    error: Optional[str]
