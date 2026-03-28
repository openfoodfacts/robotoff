import pytest
from openfoodfacts.ocr import OCRParsingException, OCRResultGenerationException

from robotoff.utils.ocr import get_ocr_result_from_url


def test_get_ocr_result_from_url_returns_none_on_parsing_error(mocker):
    mocker.patch(
        "robotoff.utils.ocr.OCRResult.from_url",
        side_effect=OCRParsingException("invalid ocr payload"),
    )

    assert (
        get_ocr_result_from_url(
            "https://images.openfoodfacts.org/images/products/000/000/000/0000/1.json",
            session=mocker.Mock(),
            error_raise=False,
        )
        is None
    )


def test_get_ocr_result_from_url_reraises_parsing_error_when_error_raise_true(mocker):
    mocker.patch(
        "robotoff.utils.ocr.OCRResult.from_url",
        side_effect=OCRParsingException("invalid ocr payload"),
    )

    with pytest.raises(OCRParsingException):
        get_ocr_result_from_url(
            "https://images.openfoodfacts.org/images/products/000/000/000/0000/1.json",
            session=mocker.Mock(),
            error_raise=True,
        )


def test_get_ocr_result_from_url_returns_none_on_generation_error(mocker):
    mocker.patch(
        "robotoff.utils.ocr.OCRResult.from_url",
        side_effect=OCRResultGenerationException(
            "Error in OCR response: {'message': 'Resource exhausted', 'code': 8}",
            "https://images.openfoodfacts.org/images/products/000/000/000/0000/1.json",
        ),
    )

    assert (
        get_ocr_result_from_url(
            "https://images.openfoodfacts.org/images/products/000/000/000/0000/1.json",
            session=mocker.Mock(),
            error_raise=False,
        )
        is None
    )


def test_get_ocr_result_from_url_reraises_generation_error_when_error_raise_true(
    mocker,
):
    exc = OCRResultGenerationException("download error", "https://example.invalid/ocr")
    mocker.patch("robotoff.utils.ocr.OCRResult.from_url", side_effect=exc)

    with pytest.raises(OCRResultGenerationException):
        get_ocr_result_from_url(
            "https://example.invalid/ocr",
            session=mocker.Mock(),
            error_raise=True,
        )
