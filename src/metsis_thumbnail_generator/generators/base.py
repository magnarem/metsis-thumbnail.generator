"""Base generator classes."""

from __future__ import annotations

from abc import ABC, abstractmethod

from metsis_thumbnail_generator.models import ThumbnailTask


class BaseThumbnailGenerator(ABC):
    """Abstract base class for all thumbnail generators."""

    @abstractmethod
    def generate(self, task: ThumbnailTask) -> bytes:
        """Generate a PNG thumbnail and return PNG bytes."""
