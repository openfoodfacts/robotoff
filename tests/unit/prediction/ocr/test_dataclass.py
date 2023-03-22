import json
import pathlib
import re
from typing import Callable, Optional

import pytest

from robotoff.prediction.ocr.dataclass import OCRParsingException, OCRResult
from robotoff.utils.fold_to_ascii import fold

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


@pytest.mark.parametrize(
    "pattern,expected_matches,preprocess_func",
    [
        (
            "fromage de chèvre frais",
            [
                [
                    "fromage ",
                    "de ",
                    "chèvre ",
                    "frais ",
                ]
            ],
            None,
        ),
        # no preprocessing, in OCR it's "Mélangez bien les pâtes" (notice the upper letter)
        ("mélangez bien les pâtes", [], None),
        (
            "mélangez bien les pâtes",
            [["Mélangez ", "bien ", "les ", "pâtes "]],
            lambda x: x.lower(),
        ),
        # Fold + lowercase should return a match
        (
            "MELANGEZ BIEN LES PATES",
            [["Mélangez ", "bien ", "les ", "pâtes "]],
            lambda x: fold(x.lower()),
        ),
        # Test that ', ' is stripped after last word ('ciboulette, ')
        ("brins de ciboulette", [["brins ", "de ", "ciboulette, "]], None),
        # Test multiple matches, we expect 2 matches
        ("rondelles", [["rondelles. "], ["rondelles "]], None),
    ],
)
def test_match(
    pattern: str,
    expected_matches: Optional[list[list[str]]],
    preprocess_func: Optional[Callable[[str], str]],
    example_ocr_result: OCRResult,
):
    matches = example_ocr_result.match(pattern, preprocess_func)

    if expected_matches is None:
        assert matches is None
    else:
        assert matches is not None
        assert len(matches) == len(expected_matches)

        for match, expected_words in zip(matches, expected_matches):
            assert [word.text for word in match] == expected_words


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
