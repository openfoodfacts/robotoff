import re
from typing import List, Dict, Tuple, Set, Optional

from flashtext import KeywordProcessor
from robotoff import settings
from robotoff.brands import BRAND_BLACKLIST_STORE
from robotoff.insights.ocr.dataclass import OCRResult, OCRRegex, OCRField
from robotoff.utils import text_file_iter, get_logger
from robotoff.utils.text import strip_accents_ascii
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def keep_brand_from_taxonomy(brand: str,
                             brand_tag: str,
                             min_length: Optional[int] = None,
                             blacklisted_brands: Optional[Set[str]] = None) -> bool:
    if brand.isdigit():
        return False

    if min_length and len(brand) < min_length:
        return False

    if blacklisted_brands is not None and brand_tag in blacklisted_brands:
        return False

    return True


def generate_brand_keyword_processor(brands: Optional[List[str]] = None,
                                     min_length: Optional[int] = None,
                                     blacklist: bool = True):
    processor = KeywordProcessor()

    blacklisted_brands: Optional[Set[str]] = None
    if blacklist:
        blacklisted_brands = BRAND_BLACKLIST_STORE.get()

    if brands is None:
        brands = text_file_iter(settings.OCR_TAXONOMY_BRANDS_PATH)

    for item in brands:
        name, key = item.split('||')
        if keep_brand_from_taxonomy(name, key, min_length, blacklisted_brands):
            processor.add_keyword(name, clean_name=(name, key))

    return processor


def get_logo_annotation_brands() -> Dict[str, str]:
    brands: Dict[str, str] = {}

    for item in text_file_iter(settings.OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH):
        if '||' in item:
            logo_description, label_tag = item.split('||')
        else:
            logger.warn("'||' separator expected!")
            continue

        brands[logo_description] = label_tag

    return brands


LOGO_ANNOTATION_BRANDS: Dict[str, str] = get_logo_annotation_brands()


def get_brand_tag(brand: str) -> str:
    brand = strip_accents_ascii(brand)
    return (brand.lower()
                 .replace(' & ', '-')
                 .replace(' ', '-')
                 .replace("'", '-'))


def brand_sort_key(item):
    """Sorting function for BRAND_DATA items.
    For the regex to work correctly, we want the longest brand names to
    appear first.
    """
    brand, _ = item

    return -len(brand), brand


def get_sorted_brands() -> List[Tuple[str, str]]:
    sorted_brands: Dict[str, str] = {}

    for item in text_file_iter(settings.OCR_BRANDS_DATA_PATH):
        if '||' in item:
            brand, regex_str = item.split('||')
        else:
            brand = item
            regex_str = re.escape(item.lower())

        sorted_brands[brand] = regex_str

    return sorted(sorted_brands.items(), key=brand_sort_key)


SORTED_BRANDS = get_sorted_brands()
BRAND_REGEX_STR = "|".join(r"((?<!\w){}(?!\w))".format(pattern)
                           for _, pattern in SORTED_BRANDS)
NOTIFY_BRANDS: Set[str] = set(
    text_file_iter(settings.OCR_BRANDS_NOTIFY_DATA_PATH))
BRAND_REGEX = OCRRegex(re.compile(BRAND_REGEX_STR),
                       field=OCRField.full_text_contiguous,
                       lowercase=True)
BRAND_PROCESSOR = generate_brand_keyword_processor(
    min_length=settings.BRAND_MATCHING_MIN_LENGTH)


def extract_brands_taxonomy(processor: KeywordProcessor,
                            text: str) -> List[JSONType]:
    insights = []

    for (brand, brand_tag), span_start, span_end in processor.extract_keywords(
            text, span_info=True):
        match_str = text[span_start:span_end]
        insights.append({
            'brand': brand,
            'brand_tag': brand_tag,
            'automatic_processing': False,
            'text': match_str,
            'data_source': "taxonomy",
            'notify': False,
        })

    return insights


def extract_brands_whitelist(ocr_regex: OCRRegex,
                             ocr_result: OCRResult,
                             sorted_brands: List[Tuple[str, str]]) -> List[JSONType]:
    insights = []
    text = ocr_result.get_text(BRAND_REGEX)

    if text:
        for match in ocr_regex.regex.finditer(text):
            groups = match.groups()

            for idx, match_str in enumerate(groups):
                if match_str is not None:
                    brand, _ = sorted_brands[idx]
                    insights.append({
                        'brand': brand,
                        'brand_tag': get_brand_tag(brand),
                        'text': match_str,
                        'notify': brand in NOTIFY_BRANDS,
                        'data_source': "whitelisted-brands",
                    })

    return insights


def extract_brands_google_cloud_vision(ocr_result: OCRResult) -> List[JSONType]:
    insights = []
    for logo_annotation in ocr_result.logo_annotations:
        if logo_annotation.description in LOGO_ANNOTATION_BRANDS:
            brand = LOGO_ANNOTATION_BRANDS[logo_annotation.description]

            insights.append({
                'brand': brand,
                'brand_tag': get_brand_tag(brand),
                'automatic_processing': False,
                'confidence': logo_annotation.score,
                'data_source': 'google-cloud-vision',
                'notify': False,
            })

    return insights


def find_brands(ocr_result: OCRResult) -> List[Dict]:
    insights = extract_brands_whitelist(BRAND_REGEX, ocr_result, SORTED_BRANDS)

    text = ocr_result.get_full_text_contiguous()
    if text:
        insights += extract_brands_taxonomy(BRAND_PROCESSOR, text)

    insights += extract_brands_google_cloud_vision(ocr_result)

    return insights
