import pytest

from robotoff.utils.image import convert_bounding_box_absolute_to_relative


@pytest.mark.parametrize(
    "bbox,width,height,expected",
    [
        # Normal case
        ((10, 20, 50, 60), 200, 100, (0.1, 0.1, 0.5, 0.3)),
        # Bounding box at origin
        ((0, 0, 50, 100), 100, 100, (0.0, 0.0, 0.5, 1.0)),
        # Bounding box exceeds image size (should be clipped to 1.0)
        ((0, 0, 200, 300), 100, 100, (0.0, 0.0, 1.0, 1.0)),
        # Negative coordinates (should be clipped to 0.0)
        ((-10, -20, 50, 100), 100, 100, (0.0, 0.0, 0.5, 1.0)),
        # Zero width/height bounding box
        ((0, 0, 0, 0), 100, 100, (0.0, 0.0, 0.0, 0.0)),
        # Bounding box is the whole image
        ((0, 0, 100, 100), 100, 100, (0.0, 0.0, 1.0, 1.0)),
        # Non-square image
        ((10, 5, 90, 45), 50, 100, (0.1, 0.1, 0.9, 0.9)),
    ],
)
def test_convert_bounding_box_absolute_to_relative(bbox, width, height, expected):
    result = convert_bounding_box_absolute_to_relative(bbox, width, height)
    assert pytest.approx(result) == expected
