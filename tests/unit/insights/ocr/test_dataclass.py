import json
import pathlib

import pytest

from robotoff.prediction.ocr.dataclass import OCRResult

data_dir = pathlib.Path(__file__).parent / "data"


@pytest.mark.parametrize("ocr_name", ["3038350013804_11.json"])
def test_ocr_result_extraction_non_regression(ocr_name: str):
    with (data_dir / ocr_name).open("r") as f:
        data = json.load(f)

    result = OCRResult.from_json(data)
    assert result
