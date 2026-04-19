from metsis_thumbnail_generator.thumbnail_path_api import (
    THUMBNAIL_PATH_CONTRACT_CASES,
    build_thumbnail_relative_path,
)


def test_thumbnail_path_contract_cases() -> None:
    for case in THUMBNAIL_PATH_CONTRACT_CASES:
        resolved = build_thumbnail_relative_path(
            metadata_identifier=case["metadata_identifier"],
            start_date=case["start_date"],
            wms_url=case["wms_url"],
        )
        assert resolved.as_posix() == case["expected_relative_path"], case["name"]
