"""Thumbnail generator implementations."""

from .base import BaseThumbnailGenerator
from .wms import WmsThumbnail

__all__ = ["BaseThumbnailGenerator", "WmsThumbnail"]
