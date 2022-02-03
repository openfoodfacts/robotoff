import re
from typing import Dict, List

from robotoff.insights.ocr.dataclass import OCRField, OCRRegex, OCRResult

TRACES_REGEX = OCRRegex(
    re.compile(
        r"(?:possibilit[ée] de traces|peut contenir(?: des traces)?|traces? [ée]ventuelles? de)"
    ),
    field=OCRField.full_text_contiguous,
    lowercase=True,
)


def find_traces(ocr_result: OCRResult) -> List[Dict]:
    results = []

    text = ocr_result.get_text(TRACES_REGEX)

    if not text:
        return []

    for match in TRACES_REGEX.regex.finditer(text):
        raw = match.group()
        end_idx = match.end()
        captured = text[end_idx : end_idx + 100]

        result = {
            "raw": raw,
            "text": captured,
            "notify": TRACES_REGEX.notify,
        }
        results.append(result)

    return results
