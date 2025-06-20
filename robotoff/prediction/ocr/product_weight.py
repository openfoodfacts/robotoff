import functools
import math
import re
from typing import Union

import pint
from openfoodfacts.ocr import (
    OCRField,
    OCRRegex,
    OCRResult,
    get_match_bounding_box,
    get_text,
)

from robotoff.types import Prediction, PredictionType
from robotoff.utils import get_logger

logger = get_logger(__name__)

# Increase version ID when introducing breaking change: changes for which we
# want old predictions to be removed in DB and replaced by newer ones
PREDICTOR_VERSION = "1"


@functools.cache
def get_unit_registry():
    # We initialize UnitRegistry here to prevent
    return pint.UnitRegistry()


def normalize_weight(value: str, unit: str) -> tuple[float, str]:
    """Normalize the product weight unit to g for mass and mL for volumes.
    Return a (value, unit) tuple, where value is the normalized value as a
    float and unit either 'g' or 'ml'."""
    if "," in value:
        # pint does not recognize ',' separator
        value = value.replace(",", ".")

    if unit == "fl oz":
        # For nutrition labeling, a fluid ounce is equal to 30 ml
        value = str(float(value) * 30)
        unit = "ml"

    ureg = get_unit_registry()
    quantity = ureg.parse_expression(f"{value} {unit}")

    if ureg.gram in quantity.compatible_units():
        normalized_quantity = quantity.to(ureg.gram)
        normalized_unit = "g"
    elif ureg.liter in quantity.compatible_units():
        normalized_quantity = quantity.to(ureg.milliliter)
        normalized_unit = "ml"
    else:
        raise ValueError(f"unknown unit: {quantity.u}")

    # Rounding errors due to float may occur with Pint,
    # round normalized value to floor if there is no significant difference
    normalized_value = normalized_quantity.magnitude
    if math.isclose(math.floor(normalized_value), normalized_value):
        normalized_value = math.floor(normalized_value)

    return normalized_value, normalized_unit


def is_valid_weight(weight_value: str) -> bool:
    """Weight values are considered invalid if one of the following rules
    is met:
    - value is not convertible to a float
    - value is negative
    - value is not an integer
    - value starts with a 0 and does not have a '.' or ',' in it
    """
    weight_value = weight_value.replace(",", ".")

    if weight_value.startswith("0") and "." not in weight_value:
        return False

    try:
        weight_value_float = float(weight_value)
    except ValueError:
        logger.warning("Weight value is not a float: %s", weight_value)
        return False

    if weight_value_float <= 0:
        logger.debug("Weight value is <= 0")
        return False

    if float(int(weight_value_float)) != weight_value_float:
        logger.info(
            "Weight value is not an integer (%s), returning non valid", weight_value
        )
        return False

    return True


def is_extreme_weight(
    normalized_value: float, unit: str, count: int | None = None
) -> bool:
    """Return True if the weight is extreme, i.e is likely wrongly detected.

    If considered extreme, a prediction won't be generated.

    :param normalized_value: the normalized weight value
    :param unit: the normalized weight unit
    :param count: the number of items in the pack, if any
    :return: True if the weight is extreme, False otherwise
    """
    if count is not None and int(count) > 20:
        # More than 20 items in a pack is quite unlikely for
        # a consumer product
        return True

    if unit == "g":
        # weights above 10 kg
        return normalized_value >= 10000 or normalized_value <= 10
    elif unit == "ml":
        # volumes above 10 l
        return normalized_value >= 10000 or normalized_value <= 10

    raise ValueError(f"invalid unit: {unit}, 'g', or 'ml' expected")


def is_suspicious_weight(normalized_value: float, unit: str) -> bool:
    """Return True is the weight is suspicious, i.e is likely wrongly
    detected."""
    if normalized_value > 1000:
        # weight value is above 1000 and
        # last digit is not 0
        # See https://github.com/openfoodfacts/robotoff/issues/43
        last_digit = str(int(normalized_value))[-1]

        if last_digit != "0":
            return True

    return False


def process_product_weight(
    match: re.Match,
    prompt: bool,
    automatic_processing: bool,
    ending_prompt: bool = False,
) -> dict | None:
    raw = match.group()

    if prompt:
        if ending_prompt:
            value = match.group(1)
            unit = match.group(2)
            prompt_str = match.group(3)

        else:
            prompt_str = match.group(1)
            value = match.group(2)
            unit = match.group(3)
    else:
        prompt_str = None
        value = match.group(1)
        unit = match.group(2)

    unit = unit.lower()
    if unit in ("dle", "cle", "mge", "mle", "ge", "kge", "le"):
        # When the e letter often comes after the weight unit, the
        # space is often not detected
        unit = unit[:-1]

    if not is_valid_weight(value):
        return None

    # Strip value from endpoint point: '525. g' -> '525 g'
    value = value.strip(".")

    text = f"{value} {unit}"
    normalized_value, normalized_unit = normalize_weight(value, unit)

    if is_extreme_weight(normalized_value, normalized_unit):
        return None

    if is_suspicious_weight(normalized_value, normalized_unit):
        # Don't process the prediction automatically if the value
        # is suspicious (very high, low,...)
        automatic_processing = False

    result = {
        "text": text,
        "raw": raw,
        "value": value,
        "unit": unit,
        "normalized_value": normalized_value,
        "normalized_unit": normalized_unit,
        "automatic_processing": automatic_processing,
    }

    if prompt_str is not None:
        result["prompt"] = prompt_str

    return result


def process_multi_packaging(match) -> dict | None:
    raw = match.group()

    count = match.group(1)
    value = match.group(2)
    unit = match.group(3).lower()

    if unit in ("dle", "cle", "mge", "mle", "ge", "kge", "le"):
        # When the e letter often comes after the weight unit, the
        # space is often not detected
        unit = unit[:-1]

    if not is_valid_weight(value):
        return None

    normalized_value, normalized_unit = normalize_weight(value, unit)

    # Check that the weight is not extreme
    if is_extreme_weight(normalized_value, normalized_unit, count):
        return None

    text = f"{count} x {value} {unit}"
    result = {
        "text": text,
        "raw": raw,
        "value": value,
        "unit": unit,
        "count": count,
        "normalized_value": normalized_value,
        "normalized_unit": normalized_unit,
        # Don't process the prediction automatically if the value
        # is suspiciously high
        "automatic_processing": not is_suspicious_weight(
            normalized_value, normalized_unit
        ),
    }

    return result


PRODUCT_WEIGHT_REGEX: dict[str, OCRRegex] = {
    "with_mention": OCRRegex(
        re.compile(
            r"(?<![a-z])(poids|poids net [aà] l'emballage|poids net|poids net égoutté|masse nette|volume net total|net weight|net wt\.?|peso neto|peso liquido|netto[ -]?gewicht)\s?:?\s?([0-9]+[,.]?[0-9]*)\s?(fl oz|dle?|cle?|mge?|mle?|lbs|oz|ge?|kge?|le?)(?![a-z])",
            re.I,
        ),
        field=OCRField.full_text_contiguous,
        processing_func=functools.partial(
            process_product_weight, prompt=True, automatic_processing=True
        ),
        priority=1,
    ),
    "with_ending_mention": OCRRegex(
        re.compile(
            r"(?<![a-z])([0-9]+[,.]?[0-9]*)\s?(fl oz|dle?|cle?|mge?|mle?|lbs|oz|ge?|kge?|le?)\s(net)(?![a-z])",
            re.I,
        ),
        field=OCRField.full_text_contiguous,
        processing_func=functools.partial(
            process_product_weight,
            prompt=True,
            ending_prompt=True,
            automatic_processing=True,
        ),
        priority=1,
    ),
    "multi_packaging": OCRRegex(
        re.compile(
            r"(?<![a-z])(\d+)\s?x\s?([0-9]+[,.]?[0-9]*)\s?(fl oz|dle?|cle?|mge?|mle?|lbs|oz|ge?|kge?|le?)(?![a-z])",
            re.I,
        ),
        field=OCRField.full_text_contiguous,
        processing_func=process_multi_packaging,
        priority=2,
    ),
    "no_mention": OCRRegex(
        re.compile(
            r"(?<![a-z])([0-9]+[,.]?[0-9]*)\s?(dle|cle|mge|mle|ge|kge)(?![a-z])", re.I
        ),
        field=OCRField.full_text_contiguous,
        processing_func=functools.partial(
            process_product_weight, prompt=False, automatic_processing=False
        ),
        priority=3,
    ),
}


def find_product_weight(content: Union[OCRResult, str]) -> list[Prediction]:
    results = []

    for type_, ocr_regex in PRODUCT_WEIGHT_REGEX.items():
        text = get_text(content, ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            if ocr_regex.processing_func is None:
                continue

            data = ocr_regex.processing_func(match)

            if data is None:
                continue

            data["matcher_type"] = type_
            data["priority"] = ocr_regex.priority
            value = data.pop("text")

            if (
                bounding_box := get_match_bounding_box(
                    content, match.start(), match.end()
                )
            ) is not None:
                data["bounding_box_absolute"] = bounding_box
            results.append(
                Prediction(
                    value=value,
                    type=PredictionType.product_weight,
                    automatic_processing=data["automatic_processing"],
                    data=data,
                    predictor="regex",
                    predictor_version=PREDICTOR_VERSION,
                )
            )

    return results
