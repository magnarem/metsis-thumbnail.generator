"""Deterministic thumbnail path utilities shared across tools."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from dateutil.parser import parse as parse_datetime

logger = logging.getLogger("metsis_thumbnail_generator.deterministic_path")

_SOLR_ID_REPLACEMENTS = (":", "/", ".")

_YEAR_MONTH_SLASH_RE = re.compile(r"/(?P<year>(?:19|20)\d{2})/(?P<month>0[1-9]|1[0-2])(?:/|$)")
_YEAR_MONTH_COMPACT_RE = re.compile(
    r"(?<!\d)(?P<year>(?:19|20)\d{2})(?P<month>0[1-9]|1[0-2])(?!\d)"
)
_YEAR_MONTH_SEPARATED_RE = re.compile(
    r"(?<!\d)(?P<year>(?:19|20)\d{2})[-_](?P<month>0[1-9]|1[0-2])(?!\d)"
)


def metadata_identifier_to_solr_id(metadata_identifier: str) -> str:
    """Return Solr-compatible id, preferring solr-indexer implementation."""
    try:
        from solrindexer.tools import to_solr_id as solrindexer_to_solr_id

        return str(solrindexer_to_solr_id(metadata_identifier))
    except Exception:
        solr_id = str(metadata_identifier)
        for token in _SOLR_ID_REPLACEMENTS:
            solr_id = solr_id.replace(token, "-")
        return solr_id


def extract_naming_authority(metadata_identifier: str) -> Optional[str]:
    """Extract naming authority prefix from metadata identifier when present."""
    if ":" not in metadata_identifier:
        return None

    prefix = metadata_identifier.split(":", 1)[0].strip()
    if not prefix:
        return None

    return prefix


def reverse_wms_host(wms_url: Optional[str]) -> Optional[str]:
    """Reverse WMS host labels after stripping port."""
    if not wms_url:
        return None

    parsed = urlparse(wms_url)
    host = parsed.hostname
    if not host:
        return None

    labels = [label for label in host.split(".") if label]
    if not labels:
        return None

    if len(labels) == 1:
        return labels[0].lower()

    return ".".join(reversed([label.lower() for label in labels]))


def _extract_year_month_from_start_date(start_date: Optional[str]) -> Optional[Tuple[str, str]]:
    if not start_date:
        return None

    try:
        dt = parse_datetime(start_date)
    except (ValueError, TypeError, OverflowError):
        return None

    return f"{dt.year:04d}", f"{dt.month:02d}"


def _extract_year_month_from_url(wms_url: Optional[str]) -> Optional[Tuple[str, str]]:
    if not wms_url:
        return None

    parsed = urlparse(wms_url)
    candidates = [parsed.path]
    if parsed.query:
        candidates.append(parsed.query)

    for candidate in candidates:
        for pattern in (_YEAR_MONTH_SLASH_RE, _YEAR_MONTH_COMPACT_RE, _YEAR_MONTH_SEPARATED_RE):
            match = pattern.search(candidate)
            if match:
                return match.group("year"), match.group("month")

    return None


def resolve_year_month(
    start_date: Optional[str],
    wms_url: Optional[str],
) -> Optional[Tuple[str, str]]:
    """Resolve year/month from start_date first, then from WMS URL."""
    from_date = _extract_year_month_from_start_date(start_date)
    if from_date is not None:
        return from_date

    return _extract_year_month_from_url(wms_url)


def build_thumbnail_relative_path(
    metadata_identifier: str,
    start_date: Optional[str],
    wms_url: Optional[str],
) -> Path:
    """Build deterministic thumbnail relative path."""
    path_segments: list[str] = []

    naming_authority = extract_naming_authority(metadata_identifier)
    if naming_authority:
        path_segments.append(naming_authority)

    reversed_host = reverse_wms_host(wms_url)
    if reversed_host:
        path_segments.append(reversed_host)

    year_month = resolve_year_month(start_date=start_date, wms_url=wms_url)
    if year_month:
        year, month = year_month
        path_segments.extend([year, month])

    file_name = f"{metadata_identifier_to_solr_id(metadata_identifier)}.png"
    path_segments.append(file_name)

    return Path(*path_segments)


def build_thumbnail_public_url(base_url: str, relative_path: Path) -> str:
    """Build public URL from base URL and relative path."""
    return f"{base_url.rstrip('/')}/{relative_path.as_posix()}"
