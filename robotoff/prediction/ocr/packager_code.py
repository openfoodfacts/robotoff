import re
from typing import Optional, Union

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.types import Prediction, PredictionType
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore

from .dataclass import OCRField, OCRRegex, OCRResult, get_match_bounding_box, get_text
from .utils import generate_keyword_processor


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


def process_fsc_match(match) -> str:
    fsc_code = match.group(1)
    return "FSC-{}".format(fsc_code).upper()


def process_USDA_match_to_flashtext(match) -> Optional[str]:
    """Returns the USDA code matched by REGEX the same way it exists
    in the USDA database (1st column of USDA_code_flashtext.txt)
    """

    unchecked_code = match.group().upper()
    unchecked_code = re.sub(r"\s*\.*", "", unchecked_code)

    processor = USDA_CODE_KEYWORD_PROCESSOR_STORE.get()
    USDA_code = extract_USDA_code(processor, unchecked_code)
    return USDA_code


def generate_USDA_code_keyword_processor() -> KeywordProcessor:
    """Builds the KeyWordProcessor for USDA codes

    This will be called only once thanks to CachedStore
    """

    codes = text_file_iter(settings.OCR_USDA_CODE_FLASHTEXT_DATA_PATH)
    return generate_keyword_processor(codes)


def extract_USDA_code(processor: KeywordProcessor, text: str) -> Optional[str]:
    """Given a string, returns the USDA code it contains or None"""
    USDA_code = None

    for (USDA_code_keyword, _) in processor.extract_keywords(text):
        USDA_code = USDA_code_keyword
        # Once we found a match we can return the code
        # as there should not be more than one match
        break
    return USDA_code


USDA_CODE_KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_USDA_code_keyword_processor, expiration_interval=None
)


PACKAGER_CODE = {
    "fr_emb": [
        OCRRegex(
            re.compile(r"emb ?(\d ?\d ?\d ?\d ?\d) ?([a-z])?(?![a-z0-9])", re.I),
            field=OCRField.full_text,
            processing_func=process_fr_emb_match,
        ),
    ],
    "fsc": [
        OCRRegex(
            re.compile(r"fsc.? ?(c\d{6})", re.I),
            field=OCRField.full_text,
            processing_func=process_fsc_match,
        ),
    ],
    "eu_fr": [
        OCRRegex(
            re.compile(
                r"fr (\d{2,3}|2[ab])[\-\s.](\d{3})[\-\s.](\d{3}) (ce|ec)(?![a-z0-9])",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
            processing_func=process_fr_packaging_match,
        ),
    ],
    "eu_de": [
        OCRRegex(
            re.compile(
                r"de (bb|be|bw|by|hb|he|hh|mv|ni|nw|rp|sh|sl|sn|st|th)[\-\s.](\d{1,5})[\-\s.] ?(eg|ec)(?![a-z0-9])",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
            processing_func=process_de_packaging_match,
        ),
    ],
    "rspo": [
        OCRRegex(
            re.compile(r"(?<!\w)RSPO-\d{7}(?!\d)"),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "fr_gluten": [
        OCRRegex(
            re.compile(r"FR-\d{3}-\d{3}"),
            field=OCRField.full_text_contiguous,
        ),
    ],
    # Temporarily disable USDA extraction until the overmatching bug is fixed
    # "USDA": [
    #     # To match the USDA like "EST. 522"
    #     OCRRegex(
    #         re.compile(r"EST\.*\s*\d{1,5}[A-Z]{0,3}\.*"),
    #         field=OCRField.full_text_contiguous,
    #         processing_func=process_USDA_match_to_flashtext,
    #     ),
    #     # To match the USDA like "V34626"
    #     OCRRegex(
    #         re.compile(r"[A-Z]\d{1,5}[A-Z]?"),
    #         field=OCRField.full_text_contiguous,
    #         processing_func=process_USDA_match_to_flashtext,
    #     ),
    # ],
}


def find_packager_codes_regex(content: Union[OCRResult, str]) -> list[Prediction]:
    results: list[Prediction] = []

    for regex_code, regex_list in PACKAGER_CODE.items():
        for ocr_regex in regex_list:
            text = get_text(content, ocr_regex)

            if not text:
                continue

            for match in ocr_regex.regex.finditer(text):
                if ocr_regex.processing_func is None:
                    value = match.group(0)
                else:
                    value = ocr_regex.processing_func(match)

                if value is not None:
                    data = {
                        "raw": match.group(0),
                        "type": regex_code,
                        "notify": ocr_regex.notify,
                    }
                    if (
                        bounding_box := get_match_bounding_box(
                            content, match.start(), match.end()
                        )
                    ) is not None:
                        data["bounding_box_absolute"] = bounding_box

                    results.append(
                        Prediction(
                            value=value,
                            data=data,
                            type=PredictionType.packager_code,
                            automatic_processing=True,
                        )
                    )

    return results


def generate_fishing_code_keyword_processor() -> KeywordProcessor:
    codes = text_file_iter(settings.OCR_FISHING_FLASHTEXT_DATA_PATH)
    return generate_keyword_processor(("{}||{}".format(c.upper(), c) for c in codes))


def extract_fishing_code(
    processor: KeywordProcessor, content: Union[OCRResult, str]
) -> list[Prediction]:
    predictions = []
    text = get_text(content)

    for (key, _), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        match_str = text[span_start:span_end]
        data = {"type": "fishing", "raw": match_str, "notify": False}
        if (
            bounding_box := get_match_bounding_box(content, span_start, span_end)
        ) is not None:
            data["bounding_box_absolute"] = bounding_box

        predictions.append(
            Prediction(
                type=PredictionType.packager_code,
                value=key,
                predictor="flashtext",
                data=data,
                automatic_processing=True,
            )
        )

    return predictions


FISHING_KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_fishing_code_keyword_processor, expiration_interval=None
)


def find_packager_codes(content: Union[OCRResult, str]) -> list[Prediction]:
    predictions = find_packager_codes_regex(content)
    processor = FISHING_KEYWORD_PROCESSOR_STORE.get()
    predictions += extract_fishing_code(processor, content)
    return predictions
