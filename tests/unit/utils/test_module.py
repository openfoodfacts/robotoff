import io

import numpy as np
import pytest
from PIL import Image

from robotoff.utils import ImageLoadingException, get_image_from_url


def test_get_image_from_url_http_error(mocker):
    session_mock = mocker.Mock()
    response_mock = mocker.Mock()
    response_mock.ok = False
    response_mock.status_code = 404
    session_mock.get.return_value = response_mock
    with pytest.raises(ImageLoadingException, match="Cannot load image.*"):
        get_image_from_url("MOCK_URL", error_raise=True, session=session_mock)

    image = get_image_from_url("MOCK_URL", error_raise=False, session=session_mock)
    assert image is None


def generate_image(height: int = 900, width: int = 800):
    image_array = np.random.randint(255, size=(height, width, 3), dtype=np.uint8)
    image = Image.fromarray(image_array)
    f = io.BytesIO()
    image.save(f, format="png")
    f.seek(0)
    return f.read()


def test_get_image_from_url(mocker):
    image_bytes = generate_image()
    session_mock = mocker.Mock()
    response_mock = mocker.Mock()
    response_mock.content = image_bytes
    response_mock.ok = True
    response_mock.status_code = 200
    session_mock.get.return_value = response_mock
    returned_image = get_image_from_url(
        "MOCK_URL", error_raise=True, session=session_mock
    )
    f = io.BytesIO()
    returned_image.save(f, format="png")
    f.seek(0)
    assert f.read() == image_bytes


def test_get_image_from_url_empty_content(mocker):
    session_mock = mocker.Mock()
    response_mock = mocker.Mock()
    response_mock.content = b""
    response_mock.ok = True
    response_mock.status_code = 200
    session_mock.get.return_value = response_mock

    with pytest.raises(ImageLoadingException, match="Cannot identify image MOCK_URL"):
        get_image_from_url("MOCK_URL", error_raise=True, session=session_mock)

    image = get_image_from_url("MOCK_URL", error_raise=False, session=session_mock)
    assert image is None


def test_get_image_from_url_invalid_content(mocker):
    session_mock = mocker.Mock()
    response_mock = mocker.Mock()
    response_mock.content = b"invalid content"
    response_mock.ok = True
    response_mock.status_code = 200
    session_mock.get.return_value = response_mock

    with pytest.raises(ImageLoadingException, match="Cannot identify image MOCK_URL"):
        get_image_from_url("MOCK_URL", error_raise=True, session=session_mock)

    image = get_image_from_url("MOCK_URL", error_raise=False, session=session_mock)
    assert image is None


def test_get_image_from_url_decompression_bomb(mocker):
    session_mock = mocker.Mock()
    response_mock = mocker.Mock()
    mocker.patch(
        "robotoff.utils.Image", **{"open.side_effect": Image.DecompressionBombError()}
    )
    response_mock.content = generate_image()
    response_mock.ok = True
    response_mock.status_code = 200
    session_mock.get.return_value = response_mock

    with pytest.raises(
        ImageLoadingException, match="Decompression bomb error for image MOCK_URL"
    ):
        get_image_from_url("MOCK_URL", error_raise=True, session=session_mock)

    image = get_image_from_url("MOCK_URL", error_raise=False, session=session_mock)
    assert image is None
