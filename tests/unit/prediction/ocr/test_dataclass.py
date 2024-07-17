import json
import pathlib
import re

import pytest
from openfoodfacts.ocr import OCRParsingException, OCRResult

data_dir = pathlib.Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def example_ocr_result():
    with (data_dir / "3038350013804_11.json").open("r") as f:
        data = json.load(f)

    yield OCRResult.from_json(data)


def test_ocr_result_extraction_non_regression(example_ocr_result):
    assert example_ocr_result


class TestOCRResult:
    def test_from_json_invalid_responses_field(self):
        with pytest.raises(
            OCRParsingException,
            match=re.escape("Responses field (list) expected in OCR JSON"),
        ):
            OCRResult.from_json({})

        with pytest.raises(
            OCRParsingException,
            match=re.escape("Responses field (list) expected in OCR JSON"),
        ):
            OCRResult.from_json({"responses": "invalid"})

    def test_from_json_empty_response(self):
        with pytest.raises(
            OCRParsingException,
            match=re.escape("Empty OCR response"),
        ):
            OCRResult.from_json({"responses": []})

    def test_from_json_error_response(self):
        with pytest.raises(
            OCRParsingException,
            match=re.escape("Error in OCR response: [{'this is an error'}"),
        ):
            OCRResult.from_json({"responses": [{"error": [{"this is an error"}]}]})


def test_word_offset(example_ocr_result: OCRResult):
    """Check that word offsets computed by Robotoff match words in
    'full text annotations' text."""
    assert example_ocr_result.full_text_annotation is not None
    text = example_ocr_result.full_text_annotation.text
    for page in example_ocr_result.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    assert text[word.start_idx : word.end_idx] == word.text
