import re
from typing import Dict, List, Union

from flashtext import KeywordProcessor

from robotoff.insights.ocr.dataclass import OCRRegex, OCRField, OCRResult, get_text
from robotoff.insights.ocr.utils import generate_keyword_processor
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType
from robotoff import settings


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


def find_packager_codes_regex(ocr_result: Union[OCRResult, str]) -> List[Dict]:
    results: List[Dict] = []

    for regex_code, ocr_regex in PACKAGER_CODE.items():
        text = get_text(ocr_result, ocr_regex)

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


def generate_fishing_code_keyword_processor() -> KeywordProcessor:
    codes = text_file_iter(settings.OCR_FISHING_FLASHTEXT_DATA_PATH)
    return generate_keyword_processor(("{}||{}".format(c.upper(), c) for c in codes))


def extract_fishing_code(processor: KeywordProcessor, text: str) -> List[JSONType]:
    insights = []

    for (key, _), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        match_str = text[span_start:span_end]
        insights.append(
            {
                "raw": match_str,
                "text": key,
                "data_source": "flashtext",
                "type": "fishing",
                "notify": True,
            }
        )

    return insights


FISHING_KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_fishing_code_keyword_processor, expiration_interval=None
)


def find_packager_codes(ocr_result: Union[OCRResult, str]) -> List[Dict]:
    insights = find_packager_codes_regex(ocr_result)
    processor = FISHING_KEYWORD_PROCESSOR_STORE.get()
    text = get_text(ocr_result)
    insights += extract_fishing_code(processor, text)
    return insights
