import functools
from typing import Dict, Iterable, List, Optional, Set, Union

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.brands import BRAND_BLACKLIST_STORE, keep_brand_from_taxonomy
from robotoff.insights import InsightType
from robotoff.insights.dataclass import RawInsight
from robotoff.insights.ocr.dataclass import get_text, OCRResult
from robotoff.insights.ocr.utils import generate_keyword_processor
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.text import get_tag

logger = get_logger(__name__)


def generate_brand_keyword_processor(
    brands: Iterable[str], blacklist: bool = True,
):
    blacklisted_brands: Optional[Set[str]] = None
    if blacklist:
        blacklisted_brands = BRAND_BLACKLIST_STORE.get()

    keep_func = functools.partial(
        keep_brand_from_taxonomy, blacklisted_brands=blacklisted_brands,
    )
    return generate_keyword_processor(brands, keep_func=keep_func)


def get_logo_annotation_brands() -> Dict[str, str]:
    brands: Dict[str, str] = {}

    for item in text_file_iter(settings.OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH):
        if "||" in item:
            logo_description, label_tag = item.split("||")
        else:
            logger.warn("'||' separator expected!")
            continue

        brands[logo_description] = label_tag

    return brands


LOGO_ANNOTATION_BRANDS: Dict[str, str] = get_logo_annotation_brands()
TAXONOMY_BRAND_PROCESSOR = generate_brand_keyword_processor(
    text_file_iter(settings.OCR_TAXONOMY_BRANDS_PATH)
)
BRAND_PROCESSOR = generate_brand_keyword_processor(
    text_file_iter(settings.OCR_BRANDS_PATH),
)


def extract_brands(
    processor: KeywordProcessor, text: str, data_source_name: str
) -> List[RawInsight]:
    insights = []

    for (brand_tag, brand), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        match_str = text[span_start:span_end]
        insights.append(
            RawInsight(
                type=InsightType.brand,
                value=brand,
                value_tag=brand_tag,
                automatic_processing=False,
                data={
                    "text": match_str,
                    "data_source": data_source_name,
                    "notify": False,
                },
            )
        )

    return insights


def extract_brands_google_cloud_vision(ocr_result: OCRResult) -> List[RawInsight]:
    insights = []
    for logo_annotation in ocr_result.logo_annotations:
        if logo_annotation.description in LOGO_ANNOTATION_BRANDS:
            brand = LOGO_ANNOTATION_BRANDS[logo_annotation.description]

            insights.append(
                RawInsight(
                    type=InsightType.brand,
                    value=brand,
                    value_tag=get_tag(brand),
                    automatic_processing=False,
                    data={
                        "confidence": logo_annotation.score,
                        "data_source": "google-cloud-vision",
                        "notify": False,
                    },
                )
            )

    return insights


def find_brands(content: Union[OCRResult, str]) -> List[RawInsight]:
    insights: List[RawInsight] = []
    text = get_text(content)

    if text:
        insights += extract_brands(BRAND_PROCESSOR, text, "curated-list")
        insights += extract_brands(TAXONOMY_BRAND_PROCESSOR, text, "taxonomy")

    if isinstance(content, OCRResult):
        insights += extract_brands_google_cloud_vision(content)

    return insights
