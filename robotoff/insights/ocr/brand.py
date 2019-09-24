import re
from typing import List, Dict, Tuple, Set

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRResult, OCRRegex, OCRField
from robotoff.utils import text_file_iter, get_logger

logger = get_logger(__name__)


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


def find_brands(ocr_result: OCRResult) -> List[Dict]:
    results = []

    text = ocr_result.get_text(BRAND_REGEX)

    if not text:
        return []

    for match in BRAND_REGEX.regex.finditer(text):
        groups = match.groups()

        for idx, match_str in enumerate(groups):
            if match_str is not None:
                brand, _ = SORTED_BRANDS[idx]
                results.append({
                    'brand': brand,
                    'brand_tag': get_brand_tag(brand),
                    'text': match_str,
                    'notify': brand in NOTIFY_BRANDS,
                })
                return results

    for logo_annotation in ocr_result.logo_annotations:
        if logo_annotation.description in LOGO_ANNOTATION_BRANDS:
            brand = LOGO_ANNOTATION_BRANDS[logo_annotation.description]

            results.append({
                'brand': brand,
                'brand_tag': get_brand_tag(brand),
                'automatic_processing': False,
                'confidence': logo_annotation.score,
                'model': 'google-cloud-vision',
                'notify': False,
            })
            return results

    return results
