"""Stable public API for deterministic thumbnail path resolution."""

from __future__ import annotations

from typing import Optional, Tuple, TypedDict

from .deterministic_path import (
    build_thumbnail_relative_path,
    metadata_identifier_to_solr_id,
)


class ThumbnailPathContractCase(TypedDict):
    """One deterministic path contract test vector."""

    name: str
    metadata_identifier: str
    start_date: Optional[str]
    wms_url: Optional[str]
    expected_relative_path: str


THUMBNAIL_PATH_CONTRACT_CASES: Tuple[ThumbnailPathContractCase, ...] = (
    {
        "name": "authority_host_and_start_date",
        "metadata_identifier": "no.met:dataset-id",
        "start_date": "2024-11-10",
        "wms_url": "https://thredds.met.no/data/wms",
        "expected_relative_path": "no.met/no.met.thredds/2024/11/no-met-dataset-id.png",
    },
    {
        "name": "url_year_month_fallback",
        "metadata_identifier": "dataset/id.1",
        "start_date": None,
        "wms_url": "https://localhost/data/202307/wms",
        "expected_relative_path": "localhost/2023/07/dataset-id-1.png",
    },
    {
        "name": "omit_year_month_when_unresolved",
        "metadata_identifier": "no.met:dataset-no-date",
        "start_date": "bad-date",
        "wms_url": "https://thredds.met.no/data/wms",
        "expected_relative_path": "no.met/no.met.thredds/no-met-dataset-no-date.png",
    },
)

__all__ = [
    "THUMBNAIL_PATH_CONTRACT_CASES",
    "ThumbnailPathContractCase",
    "build_thumbnail_relative_path",
    "metadata_identifier_to_solr_id",
]
