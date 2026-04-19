"""Metsis thumbnail generator package."""

from .thumbnail_path_api import (
    THUMBNAIL_PATH_CONTRACT_CASES,
    build_thumbnail_relative_path,
    metadata_identifier_to_solr_id,
)

__all__ = [
    "__version__",
    "THUMBNAIL_PATH_CONTRACT_CASES",
    "build_thumbnail_relative_path",
    "metadata_identifier_to_solr_id",
]

__version__ = "0.1.0"
