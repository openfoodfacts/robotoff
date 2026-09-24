import datetime
import functools
import re

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
PREDICTOR_VERSION = "1"

# A detected date is only kept as an expiration date if its year falls within a
# plausible window around the current date. Best-before / expiration dates are
# usually in the future, but can be slightly in the past for products still on
# shelves, so we allow a small margin on both sides. Dates far outside this
# window are almost always OCR noise or an unrelated date (e.g. a manufacturing
# lot number misread as a date).
#
# The window is computed relative to the current date (see
# `is_plausible_expiration_date`) rather than hardcoded, so it never becomes
# stale: a previous hardcoded upper bound silently dropped every date from the
# then-future once that year arrived.
MAX_YEARS_IN_PAST = 5
MAX_YEARS_IN_FUTURE = 15


def is_plausible_expiration_date(
    date: datetime.date, today: datetime.date | None = None
) -> bool:
    """Return True if `date` is a plausible expiration date, i.e. its year is
    within `MAX_YEARS_IN_PAST` years before and `MAX_YEARS_IN_FUTURE` years
    after the current year.

    :param date: the candidate expiration date
    :param today: the reference date, defaults to `datetime.date.today()`
        (mainly useful for testing)
    """
    if today is None:
        today = datetime.date.today()

    return (
        today.year - MAX_YEARS_IN_PAST <= date.year <= today.year + MAX_YEARS_IN_FUTURE
    )


def process_full_digits_expiration_date(match, short: bool) -> datetime.date | None:
    day, month, year = match.group(1, 2, 3)

    if short:
        format_str: str = "%d/%m/%y"
    else:
        format_str = "%d/%m/%Y"

    try:
        date = datetime.datetime.strptime(f"{day}/{month}/{year}", format_str).date()
    except ValueError:
        return None

    return date


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


def find_expiration_date(content: OCRResult | str) -> list[Prediction]:
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

            date = ocr_regex.processing_func(match)

            if date is None:
                continue

            if not is_plausible_expiration_date(date):
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
