import logging
import re
from typing import Union

from openfoodfacts.ocr import (
    OCRField,
    OCRRegex,
    OCRResult,
    get_match_bounding_box,
    get_text,
)

from robotoff.off import normalize_tag
from robotoff.taxonomy import TaxonomyType, match_taxonomized_value
from robotoff.types import JSONType, Prediction, PredictionType

logger = logging.getLogger(__name__)


# Increase version ID when introducing breaking change: changes for which we
# want old predictions to be removed in DB and replaced by newer ones
PREDICTOR_VERSION = "1"


def category_taxonomisation(lang, match) -> str | None:
    """Function to match categories detected via AOP REGEX with categories
    taxonomy database. If no match is possible, we return None.
    """

    unchecked_category = lang + normalize_tag(match.group("category"))

    return match_taxonomized_value(unchecked_category, TaxonomyType.category.name)


AOC_REGEX = {
    "fr:": [
        OCRRegex(
            # re.compile(r"(?<=appellation\s).*(?=(\scontr[ôo]l[ée]e)|(\sprot[ée]g[ée]e))"),
            re.compile(
                r"(appellation)\s*(?P<category>.+)\s*(contr[ôo]l[ée]e|prot[ée]g[ée]e)",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
            processing_func=category_taxonomisation,
        ),
        OCRRegex(
            re.compile(
                r"(?P<category>.+)\s*(appellation d'origine contr[ôo]l[ée]e|appellation d'origine prot[ée]g[ée]e)",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
            processing_func=category_taxonomisation,
        ),
    ],
    "es:": [
        OCRRegex(
            re.compile(r"(?P<category>.+)(\s*denominacion de origen protegida)", re.I),
            field=OCRField.full_text_contiguous,
            processing_func=category_taxonomisation,
        ),
        OCRRegex(
            re.compile(r"(denominacion de origen protegida\s*)(?P<category>.+)", re.I),
            field=OCRField.full_text_contiguous,
            processing_func=category_taxonomisation,
        ),
    ],
    "en:": [
        OCRRegex(
            re.compile(r"(?P<category>.+)\s*(aop|dop|pdo)", re.I),
            field=OCRField.full_text_contiguous,
            processing_func=category_taxonomisation,
        ),
        OCRRegex(
            re.compile(r"(aop|dop|pdo)\s*(?P<category>.+)", re.I),
            field=OCRField.full_text_contiguous,
            processing_func=category_taxonomisation,
        ),
    ],
}


def find_category(content: Union[OCRResult, str]) -> list[Prediction]:
    """This function returns a prediction of the product category.
    For now we are extracting categories via REGEX
    only thanks to an AOP syntax but we may find in the future
    other ways to get sure prediction of categories.
    """

    predictions = []

    for lang, regex_list in AOC_REGEX.items():
        for ocr_regex in regex_list:
            text = get_text(content, ocr_regex)

            if not text:
                continue

            for match in ocr_regex.regex.finditer(text):
                if ocr_regex.processing_func:
                    category_value = ocr_regex.processing_func(lang, match)

                if category_value is None:
                    continue

                data: JSONType = {"text": match.group()}
                if (
                    bounding_box := get_match_bounding_box(
                        content, match.start(), match.end()
                    )
                ) is not None:
                    data["bounding_box_absolute"] = bounding_box

                predictions.append(
                    Prediction(
                        type=PredictionType.category,
                        value_tag=category_value,
                        predictor="regex",
                        data=data,
                        automatic_processing=False,
                        predictor_version=PREDICTOR_VERSION,
                    )
                )
    return predictions
