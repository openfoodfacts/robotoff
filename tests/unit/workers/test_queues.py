import pytest

from robotoff.types import ProductIdentifier, ServerType
from robotoff.workers.queues import get_high_queue


@pytest.mark.parametrize(
    "barcode,queue_name",
    [
        ("3456300016208", "robotoff-high-1"),
        ("3456300016212", "robotoff-high-2"),
        ("3456300016214", "robotoff-high-3"),
        ("3456300016210", "robotoff-high-4"),
        # check that it works too with non digit barcodes
        ("prefix_3456300016210", "robotoff-high-3"),
    ],
)
def test_get_high_queue(barcode: str, queue_name: str):
    assert (
        get_high_queue(
            ProductIdentifier(barcode=barcode, server_type=ServerType.off)
        ).name
        == queue_name
    )
