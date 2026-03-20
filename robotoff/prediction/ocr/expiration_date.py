import datetime
import functools
import re
from typing import Union

from openfoodfacts.ocr import (
    OCRField,
    OCRRegex,
    OCRResult,
    get_match_bounding_box,
    get_text,
)

from robotoff.types import JSONType, Prediction, PredictionType

# Increase version ID when introducing breaking change: changes for which we
# want old predictions to be removed in DB and replaced by newer ones
PREDICTOR_VERSION = "2"

GERMAN_DATE_HINTS = (
    "mindestens haltbar",
    "haltbar bis",
    "mhd",
)


def process_full_digits_expiration_date(
    match,
    short: bool,
    date_orders: tuple[str, ...] = ("dmy",),
) -> datetime.date | None:
    day, month, year = match.group(1, 2, 3)

    format_map = {
        "dmy": "%d/%m/%y" if short else "%d/%m/%Y",
        "mdy": "%m/%d/%y" if short else "%m/%d/%Y",
    }

    for date_order in date_orders:
        format_str = format_map.get(date_order)
        if format_str is None:
            continue

        try:
            return datetime.datetime.strptime(
                "{}/{}/{}".format(day, month, year), format_str
            ).date()
        except ValueError:
            continue

    return None


def get_date_orders(raw: str, text: str) -> tuple[str, ...]:
    separator_match = re.search(r"[-./]", raw)
    separator = separator_match.group(0) if separator_match is not None else None
    lowered_text = text.casefold()

    if separator == "/" and any(hint in lowered_text for hint in GERMAN_DATE_HINTS):
        return tuple()

    return ("dmy",)


EXPIRATION_DATE_REGEX: dict[str, OCRRegex] = {
    "full_digits_short": OCRRegex(
        re.compile(r"(?<!\d)(\d{2})[-./](\d{2})[-./](\d{2})(?!\d)"),
        field=OCRField.full_text,
        processing_func=functools.partial(
            process_full_digits_expiration_date, short=True
        ),
    ),
    "full_digits_long": OCRRegex(
        re.compile(r"(?<!\d)(\d{2})[-./](\d{2})[-./](\d{4})(?!\d)"),
        field=OCRField.full_text,
        processing_func=functools.partial(
            process_full_digits_expiration_date, short=False
        ),
    ),
}


def find_expiration_date(content: Union[OCRResult, str]) -> list[Prediction]:
    # Parse expiration date
    #        "À consommer de préférence avant",
    results: list[Prediction] = []

    for type_, ocr_regex in EXPIRATION_DATE_REGEX.items():
        text = get_text(content, ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            raw = match.group(0)

            if not ocr_regex.processing_func:
                continue

            date_orders = get_date_orders(raw, text)
            date = ocr_regex.processing_func(match, date_orders=date_orders)

            if date is None:
                continue

            if date.year > 2025 or date.year < 2015:
                continue

            # Format dates according to ISO 8601
            value = date.strftime("%Y-%m-%d")

            data: JSONType = {"raw": raw, "type": type_}
            if (
                bounding_box := get_match_bounding_box(
                    content, match.start(), match.end()
                )
            ) is not None:
                data["bounding_box_absolute"] = bounding_box
            results.append(
                Prediction(
                    value=value,
                    type=PredictionType.expiration_date,
                    data=data,
                    automatic_processing=True,
                    predictor="regex",
                    predictor_version=PREDICTOR_VERSION,
                )
            )

    return results
