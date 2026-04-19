from pathlib import Path

from metsis_thumbnail_generator.models import ThumbnailTask
from metsis_thumbnail_generator.output_handlers import ThumbnailOutput


def test_resolve_storage_path_uses_deterministic_segments(tmp_path: Path) -> None:
    output = ThumbnailOutput(base_path=tmp_path, base_url=None)
    task = ThumbnailTask(
        metadata_identifier="no.met:test-id",
        start_date="2024-11-10",
        wms_url="https://example.test/wms",
    )

    destination = output.resolve_storage_path(task=task)

    assert destination == tmp_path / "no.met" / "test.example" / "2024" / "11" / "no-met-test-id.png"
