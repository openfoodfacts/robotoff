import re
from typing import Dict, List

from robotoff.insights.ocr.dataclass import OCRField, OCRRegex, OCRResult


def process_fr_packaging_match(match) -> str:
    approval_numbers = match.group(1, 2, 3)
    return "FR {}.{}.{} EC".format(*approval_numbers).upper()


def process_de_packaging_match(match) -> str:
    federal_state_tag, company_tag = match.group(1, 2)

    return "DE {}-{} EC".format(federal_state_tag, company_tag).upper()


def process_fr_emb_match(match) -> str:
    city_code, company_code = match.group(1, 2)
    city_code = city_code.replace(" ", "")
    company_code = company_code or ""
    return "EMB {}{}".format(city_code, company_code).upper()


PACKAGER_CODE: Dict[str, OCRRegex] = {
    "fr_emb": OCRRegex(
        re.compile(r"emb ?(\d ?\d ?\d ?\d ?\d) ?([a-z])?(?![a-z0-9])"),
        field=OCRField.text_annotations,
        lowercase=True,
        processing_func=process_fr_emb_match,
    ),
    "eu_fr": OCRRegex(
        re.compile(
            r"fr (\d{2,3}|2[ab])[\-\s.](\d{3})[\-\s.](\d{3}) (ce|ec)(?![a-z0-9])"
        ),
        field=OCRField.full_text_contiguous,
        lowercase=True,
        processing_func=process_fr_packaging_match,
    ),
    "eu_de": OCRRegex(
        re.compile(
            r"de (bb|be|bw|by|hb|he|hh|mv|ni|nw|rp|sh|sl|sn|st|th)[\-\s.](\d{1,5})[\-\s.] ?(eg|ec)(?![a-z0-9])"
        ),
        field=OCRField.full_text_contiguous,
        lowercase=True,
        processing_func=process_de_packaging_match,
    ),
}


def find_packager_codes(ocr_result: OCRResult) -> List[Dict]:
    results = []

    for regex_code, ocr_regex in PACKAGER_CODE.items():
        text = ocr_result.get_text(ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            if ocr_regex.processing_func is not None:
                value = ocr_regex.processing_func(match)
                results.append(
                    {
                        "raw": match.group(0),
                        "text": value,
                        "type": regex_code,
                        "notify": ocr_regex.notify,
                    }
                )

    return results
