import datetime
import functools
import re
from typing import Dict, List, Optional, Union

from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import RawInsight
from robotoff.insights.ocr.dataclass import get_text, OCRField, OCRRegex, OCRResult


def process_full_digits_expiration_date(match, short: bool) -> Optional[datetime.date]:
    day, month, year = match.group(1, 2, 3)

    if short:
        format_str: str = "%d/%m/%y"
    else:
        format_str = "%d/%m/%Y"

    try:
        date = datetime.datetime.strptime(
            "{}/{}/{}".format(day, month, year), format_str
        ).date()
    except ValueError:
        return None

    return date


EXPIRATION_DATE_REGEX: Dict[str, OCRRegex] = {
    "full_digits_short": OCRRegex(
        re.compile(r"(?<!\d)(\d{2})[-./](\d{2})[-./](\d{2})(?!\d)"),
        field=OCRField.full_text,
        lowercase=False,
        processing_func=functools.partial(
            process_full_digits_expiration_date, short=True
        ),
    ),
    "full_digits_long": OCRRegex(
        re.compile(r"(?<!\d)(\d{2})[-./](\d{2})[-./](\d{4})(?!\d)"),
        field=OCRField.full_text,
        lowercase=False,
        processing_func=functools.partial(
            process_full_digits_expiration_date, short=False
        ),
    ),
}


def find_expiration_date(content: Union[OCRResult, str]) -> List[RawInsight]:
    # Parse expiration date
    #        "À consommer de préférence avant",
    results: List[RawInsight] = []

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

            if date.year > 2025 or date.year < 2015:
                continue

            # Format dates according to ISO 8601
            value = date.strftime("%Y-%m-%d")

            results.append(
                RawInsight(
                    value=value,
                    type=InsightType.expiration_date,
                    data={"raw": raw, "type": type_, "notify": ocr_regex.notify},
                )
            )

    return results
