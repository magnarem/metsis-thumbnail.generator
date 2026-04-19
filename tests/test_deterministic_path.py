from pathlib import Path

from metsis_thumbnail_generator.deterministic_path import (
    build_thumbnail_relative_path,
    resolve_year_month,
)


def test_resolve_year_month_prefers_start_date() -> None:
    year_month = resolve_year_month(
        start_date="2024-11-10",
        wms_url="https://thredds.met.no/data/2001/02/wms?service=WMS",
    )

    assert year_month == ("2024", "11")


def test_resolve_year_month_uses_wms_url_fallback() -> None:
    year_month = resolve_year_month(
        start_date=None,
        wms_url="https://thredds.met.no/data/2023/07/wms?service=WMS",
    )

    assert year_month == ("2023", "07")


def test_build_thumbnail_relative_path_without_authority_or_year_month() -> None:
    path = build_thumbnail_relative_path(
        metadata_identifier="dataset-without-authority",
        start_date=None,
        wms_url="https://localhost/wms",
    )

    assert path == Path("localhost") / "dataset-without-authority.png"
