from metsis_thumbnail_generator.models import ThumbnailTask
from metsis_thumbnail_generator.worker import worker_main


def test_worker_main_returns_not_implemented_error(monkeypatch):
    class FakeQueue:
        def __init__(self, items):
            self.items = items

        def get(self):
            return self.items.pop(0)

    class ResultQueue:
        def __init__(self):
            self.items = []

        def put(self, item):
            self.items.append(item)

    task = ThumbnailTask("id-1", "2024-01-01", "https://example.test/wms")
    task_queue = FakeQueue([task, None])
    result_queue = ResultQueue()

    worker_main(
        task_queue=task_queue,
        result_queue=result_queue,
        wms_projection="PlateCarree",
        wms_layer=None,
        wms_style=None,
        wms_zoom=0.0,
        wms_coastlines=False,
        wms_extent=None,
    )

    assert len(result_queue.items) == 1
    assert result_queue.items[0].metadata_identifier == "id-1"
    assert result_queue.items[0].error is not None
    assert result_queue.items[0].png_bytes is None
