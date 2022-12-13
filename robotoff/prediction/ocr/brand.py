import functools
from typing import Iterable, Optional, Union

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.brands import BRAND_BLACKLIST_STORE, keep_brand_from_taxonomy
from robotoff.prediction.types import Prediction
from robotoff.types import PredictionType
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.text import get_tag

from .dataclass import OCRResult, get_text
from .utils import generate_keyword_processor

logger = get_logger(__name__)


def generate_brand_keyword_processor(
    brands: Iterable[str],
    blacklist: bool = True,
):
    blacklisted_brands: Optional[set[str]] = None
    if blacklist:
        blacklisted_brands = BRAND_BLACKLIST_STORE.get()

    keep_func = functools.partial(
        keep_brand_from_taxonomy,
        blacklisted_brands=blacklisted_brands,
    )
    return generate_keyword_processor(brands, keep_func=keep_func)


def get_logo_annotation_brands() -> dict[str, str]:
    brands: dict[str, str] = {}

    for item in text_file_iter(settings.OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH):
        if "||" in item:
            logo_description, label_tag = item.split("||")
        else:
            logger.warning("'||' separator expected!")
            continue

        brands[logo_description] = label_tag

    return brands


LOGO_ANNOTATION_BRANDS: dict[str, str] = get_logo_annotation_brands()
TAXONOMY_BRAND_PROCESSOR = generate_brand_keyword_processor(
    text_file_iter(settings.OCR_TAXONOMY_BRANDS_PATH)
)
BRAND_PROCESSOR = generate_brand_keyword_processor(
    text_file_iter(settings.OCR_BRANDS_PATH),
)


def extract_brands(
    processor: KeywordProcessor,
    text: str,
    data_source_name: str,
    automatic_processing: bool,
) -> list[Prediction]:
    predictions = []

    for (brand_tag, brand), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        match_str = text[span_start:span_end]
        predictions.append(
            Prediction(
                type=PredictionType.brand,
                value=brand,
                value_tag=brand_tag,
                automatic_processing=automatic_processing,
                predictor=data_source_name,
                data={"text": match_str, "notify": False},
            )
        )

    return predictions


def extract_brands_google_cloud_vision(ocr_result: OCRResult) -> list[Prediction]:
    predictions = []
    for logo_annotation in ocr_result.logo_annotations:
        if logo_annotation.description in LOGO_ANNOTATION_BRANDS:
            brand = LOGO_ANNOTATION_BRANDS[logo_annotation.description]

            predictions.append(
                Prediction(
                    type=PredictionType.brand,
                    value=brand,
                    value_tag=get_tag(brand),
                    automatic_processing=False,
                    predictor="google-cloud-vision",
                    data={"confidence": logo_annotation.score, "notify": False},
                )
            )

    return predictions


def find_brands(content: Union[OCRResult, str]) -> list[Prediction]:
    predictions: list[Prediction] = []
    text = get_text(content)

    if text:
        predictions += extract_brands(
            BRAND_PROCESSOR, text, "curated-list", automatic_processing=True
        )
        predictions += extract_brands(
            TAXONOMY_BRAND_PROCESSOR, text, "taxonomy", automatic_processing=False
        )

    if isinstance(content, OCRResult):
        predictions += extract_brands_google_cloud_vision(content)

    return predictions
