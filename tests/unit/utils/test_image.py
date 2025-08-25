import io

import numpy as np
import PIL
import pytest

from robotoff.utils.download import AssetLoadingException
from robotoff.utils.image import (
    convert_bounding_box_absolute_to_relative,
    get_image_from_url,
)


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


class TestGetImageFromURL:
    def test_no_cache_valid_image(self, mocker):
        image = PIL.Image.new("RGB", (100, 100))
        image_fp = io.BytesIO()
        image.save(image_fp, format="JPEG")
        image_fp.seek(0)
        image_bytes = image_fp.read()
        mocker.patch(
            "robotoff.utils.image.get_asset_from_url",
            return_value=type(
                "Response",
                (),
                {"ok": True, "content": image_bytes},
            )(),
        )

        output_pil = get_image_from_url(
            "http://example.com/image.jpg", use_cache=False, return_type="PIL"
        )
        assert isinstance(output_pil, PIL.Image.Image)
        assert output_pil.size == (100, 100)
        assert output_pil.mode == "RGB"

        output_np = get_image_from_url(
            "http://example.com/image.jpg", use_cache=False, return_type="np"
        )
        assert isinstance(output_np, np.ndarray)
        assert output_np.shape == (100, 100, 3)
        assert output_np.dtype == np.uint8
        assert (output_np[0, 0] == [0, 0, 0]).all()

        output_bytes = get_image_from_url(
            "http://example.com/image.jpg", use_cache=False, return_type="bytes"
        )
        assert isinstance(output_bytes, bytes)
        assert output_bytes == image_bytes

    def test_no_cache_invalid_image(self, mocker):
        image_bytes = b"notanimage"
        mocker.patch(
            "robotoff.utils.image.get_asset_from_url",
            return_value=type(
                "Response",
                (),
                {"ok": True, "content": image_bytes},
            )(),
        )

        with pytest.raises(AssetLoadingException):
            get_image_from_url(
                "http://example.com/image.jpg", use_cache=False, return_type="PIL"
            )

        with pytest.raises(AssetLoadingException):
            get_image_from_url(
                "http://example.com/image.jpg", use_cache=False, return_type="np"
            )

        output_pil = get_image_from_url(
            "http://example.com/image.jpg", use_cache=False, return_type="bytes"
        )
        assert isinstance(output_pil, bytes)
        assert output_pil == image_bytes
