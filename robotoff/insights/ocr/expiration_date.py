import datetime
import functools
import re
from typing import List, Dict, Optional

from robotoff.insights.ocr.dataclass import OCRResult, OCRRegex, OCRField


def process_full_digits_expiration_date(match, short: bool) -> Optional[datetime.date]:
    day, month, year = match.group(1, 2, 3)

    if short:
        format_str: str = "%d/%m/%y"
    else:
        format_str = "%d/%m/%Y"

    try:
        date = datetime.datetime.strptime("{}/{}/{}".format(day, month, year), format_str).date()
    except ValueError:
        return None

    return date


EXPIRATION_DATE_REGEX: Dict[str, OCRRegex] = {
    'full_digits_short': OCRRegex(re.compile(r'(?<!\d)(\d{2})[-./](\d{2})[-./](\d{2})(?!\d)'),
                                  field=OCRField.full_text,
                                  lowercase=False,
                                  processing_func=functools.partial(process_full_digits_expiration_date,
                                                                    short=True)),
    'full_digits_long': OCRRegex(re.compile(r'(?<!\d)(\d{2})[-./](\d{2})[-./](\d{4})(?!\d)'),
                                 field=OCRField.full_text,
                                 lowercase=False,
                                 processing_func=functools.partial(process_full_digits_expiration_date,
                                                                   short=False)),
}


def find_expiration_date(ocr_result: OCRResult) -> List[Dict]:
    # Parse expiration date
    #        "À consommer de préférence avant",
    results = []

    for type_, ocr_regex in EXPIRATION_DATE_REGEX.items():
        text = ocr_result.get_text(ocr_regex)

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

            results.append({
                "raw": raw,
                "text": value,
                "type": type_,
                "notify": ocr_regex.notify,
            })

    return results
