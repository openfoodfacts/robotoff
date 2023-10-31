import pytest

from robotoff.workers.tasks.import_image import get_text_from_bounding_box

from ...pytest_utils import get_ocr_result_asset


@pytest.mark.parametrize(
    "ocr_asset_path, bounding_box, image_width, image_height, expected_text",
    [
        (
            "/main/robotoff/tests/unit/ocr/5400910301160_1.json",
            (
                0.2808293402194977,
                0.37121888995170593,
                0.35544055700302124,
                0.49409016966819763,
            ),
            882,
            1200,
            "NUTRIDIA ",
        ),
        (
            "/main/robotoff/tests/unit/ocr/9421023629015_5.json",
            (0.342327416, 0.469950765, 0.512927711, 0.659323752),
            901,
            1200,
            "manuka health\nNEW ZEALAND\n",
        ),
    ],
)
def test_get_text_from_bounding_box(
    ocr_asset_path: str,
    bounding_box: tuple[int, int, int, int],
    expected_text: str,
    image_width: int,
    image_height: int,
):
    ocr_result = get_ocr_result_asset(ocr_asset_path)
    text = get_text_from_bounding_box(
        ocr_result, bounding_box, image_width, image_height
    )
    assert text == expected_text
