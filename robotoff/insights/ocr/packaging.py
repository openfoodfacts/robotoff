from typing import List, Dict, Optional

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRField, OCRResult
from robotoff.insights.ocr.utils import generate_keyword_processor

from robotoff.insights.ocr.utils import get_tag
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore


def generate_packaging_keyword_processor(packaging: Optional[List[str]] = None):
    if packaging is None:
        packaging = text_file_iter(settings.OCR_PACKAGING_DATA_PATH)

    return generate_keyword_processor(packaging)


KEYWORD_PROCESSOR_STORE = CachedStore(fetch_func=generate_packaging_keyword_processor,
                                      expiration_interval=None)


def find_packaging(ocr_result: OCRResult) -> List[Dict]:
    insights = []

    text = ocr_result._get_text(OCRField.full_text_contiguous, lowercase=True)

    if not text:
        return []

    processor = KEYWORD_PROCESSOR_STORE.get()

    for (packaging_str, _), span_start, span_end in processor.extract_keywords(
            text, span_info=True):
        packagings = packaging_str.split(';')

        for packaging in packagings:
            match_str = text[span_start:span_end]
            insights.append({
                'packaging_tag': get_tag(packaging),
                'packaging': packaging,
                'text': match_str,
                'notify': True,
                'automatic_processing': True,
            })

    return insights
