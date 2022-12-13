import re
from typing import Optional, Union

from robotoff.off import normalize_tag
from robotoff.prediction.types import Prediction
from robotoff.taxonomy import get_taxonomy
from robotoff.types import PredictionType
from robotoff.utils import get_logger

from .dataclass import OCRField, OCRRegex, OCRResult, get_text

logger = get_logger(__name__)


def category_taxonomisation(lang, match) -> Optional[str]:
    """Function to match categories detected via AOP REGEX with categories
    taxonomy database. If no match is possible, we return None.
    """

    unchecked_category = lang + normalize_tag(match.group("category"))

    checked_category = get_taxonomy("category").nodes.get(unchecked_category)

    # TODO: We may want to create a utility function in Taxonomy  to match
    # also with synonyms of the category existing in the taxonomy

    if checked_category is not None:
        return checked_category.id

    return None


AOC_REGEX = {
    "fr:": [
        OCRRegex(
            # re.compile(r"(?<=appellation\s).*(?=(\scontr[ôo]l[ée]e)|(\sprot[ée]g[ée]e))"),
            re.compile(
                r"(appellation)\s*(?P<category>.+)\s*(contr[ôo]l[ée]e|prot[ée]g[ée]e)"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
            processing_func=category_taxonomisation,
        ),
        OCRRegex(
            re.compile(
                r"(?P<category>.+)\s*(appellation d'origine contr[ôo]l[ée]e|appellation d'origine prot[ée]g[ée]e)"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
            processing_func=category_taxonomisation,
        ),
    ],
    "es:": [
        OCRRegex(
            re.compile(r"(?P<category>.+)(\s*denominacion de origen protegida)"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
            processing_func=category_taxonomisation,
        ),
        OCRRegex(
            re.compile(r"(denominacion de origen protegida\s*)(?P<category>.+)"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
            processing_func=category_taxonomisation,
        ),
    ],
    "en:": [
        OCRRegex(
            re.compile(r"(?P<category>.+)\s*(aop|dop|pdo)"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
            processing_func=category_taxonomisation,
        ),
        OCRRegex(
            re.compile(r"(aop|dop|pdo)\s*(?P<category>.+)"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
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

                predictions.append(
                    Prediction(
                        type=PredictionType.category,
                        value_tag=category_value,
                        predictor="regex",
                        data={"text": match.group(), "notify": ocr_regex.notify},
                        automatic_processing=False,
                    )
                )
    return predictions
