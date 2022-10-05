import json
import pathlib
import re

import pytest

from robotoff.prediction.ocr.dataclass import OCRParsingException, OCRResult

data_dir = pathlib.Path(__file__).parent / "data"


@pytest.mark.parametrize("ocr_name", ["3038350013804_11.json"])
def test_ocr_result_extraction_non_regression(ocr_name: str):
    with (data_dir / ocr_name).open("r") as f:
        data = json.load(f)

    result = OCRResult.from_json(data)
    assert result


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
