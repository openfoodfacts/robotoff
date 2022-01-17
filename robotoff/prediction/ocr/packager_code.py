import re
from typing import Dict, List, Union

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore

from .dataclass import OCRField, OCRRegex, OCRResult, get_text
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


PACKAGER_CODE: Dict[str, OCRRegex] = {
    "fr_emb": OCRRegex(
        re.compile(r"emb ?(\d ?\d ?\d ?\d ?\d) ?([a-z])?(?![a-z0-9])"),
        field=OCRField.text_annotations,
        lowercase=True,
        processing_func=process_fr_emb_match,
    ),
    "fsc": OCRRegex(
        re.compile(r"fsc.? ?(c\d{6})"),
        field=OCRField.text_annotations,
        lowercase=True,
        processing_func=process_fsc_match,
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
    "rspo": OCRRegex(
        re.compile(r"(?<!\w)RSPO-\d{7}(?!\d)"),
        field=OCRField.full_text_contiguous,
        lowercase=False,
    ),
}


def find_packager_codes_regex(ocr_result: Union[OCRResult, str]) -> List[Prediction]:
    results: List[Prediction] = []

    for regex_code, ocr_regex in PACKAGER_CODE.items():
        text = get_text(ocr_result, ocr_regex, ocr_regex.lowercase)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            if ocr_regex.processing_func is None:
                value = match.group(0)
            else:
                value = ocr_regex.processing_func(match)

            results.append(
                Prediction(
                    value=value,
                    data={
                        "raw": match.group(0),
                        "type": regex_code,
                        "notify": ocr_regex.notify,
                    },
                    type=PredictionType.packager_code,
                    automatic_processing=True,
                )
            )

    return results


def generate_fishing_code_keyword_processor() -> KeywordProcessor:
    codes = text_file_iter(settings.OCR_FISHING_FLASHTEXT_DATA_PATH)
    return generate_keyword_processor(("{}||{}".format(c.upper(), c) for c in codes))


def extract_fishing_code(processor: KeywordProcessor, text: str) -> List[Prediction]:
    predictions = []

    for (key, _), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        match_str = text[span_start:span_end]
        predictions.append(
            Prediction(
                type=PredictionType.packager_code,
                value=key,
                predictor="flashtext",
                data={"type": "fishing", "raw": match_str, "notify": False},
                automatic_processing=True,
            )
        )

    return predictions


FISHING_KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_fishing_code_keyword_processor, expiration_interval=None
)


def find_packager_codes(ocr_result: Union[OCRResult, str]) -> List[Prediction]:
    predictions = find_packager_codes_regex(ocr_result)
    processor = FISHING_KEYWORD_PROCESSOR_STORE.get()
    text = get_text(ocr_result)
    predictions += extract_fishing_code(processor, text)
    return predictions
