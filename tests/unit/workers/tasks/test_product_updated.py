import pytest

from robotoff.types import ProductIdentifier, ServerType
from robotoff.workers.tasks.product_updated import should_rerun_category_predictor

DEFAULT_BARCODE = "123"
DEFAULT_PRODUCT_ID = ProductIdentifier(DEFAULT_BARCODE, ServerType.off)


@pytest.mark.parametrize(
    "diffs, expected",
    [
        (None, True),
        ({}, False),
        ({"fields": {"change": ["product_name"]}}, True),
        ({"fields": {"change": ["labels"]}}, False),
        ({"fields": {"add": ["labels"]}}, False),
        (
            {
                "fields": {
                    "add": ["ingredients_text_it"],
                    "change": ["ingredients_text"],
                }
            },
            True,
        ),
        (
            {
                "fields": {
                    "add": ["product_name", "product_name_fr"],
                }
            },
            True,
        ),
        ({"nutrition": {"add": ["input_sets", "aggregated_set"]}}, True),
        ({"nutrition": {"delete": ["input_sets", "aggregated_set"]}}, True),
        ({"nutrition": {"change": ["input_sets", "aggregated_set"]}}, True),
        ({"uploaded_images": {"delete": ["2"]}}, True),
        ({"uploaded_images": {"add": ["2"]}}, True),
    ],
)
def test_should_rerun_category_predictor(diffs, expected):
    assert should_rerun_category_predictor(diffs) is expected
