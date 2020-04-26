from typing import List, Dict, Optional, Union

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRResult, get_text
from robotoff.insights.ocr.utils import generate_keyword_processor

from robotoff.insights.ocr.utils import get_tag
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore


def generate_packaging_keyword_processor(packaging: Optional[List[str]] = None):
    if packaging is None:
        packaging = text_file_iter(settings.OCR_PACKAGING_DATA_PATH)

    return generate_keyword_processor(packaging)


KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_packaging_keyword_processor, expiration_interval=None
)


def find_packaging(content: Union[OCRResult, str]) -> List[Dict]:
    insights = []

    text = get_text(content)

    if not text:
        return []

    processor = KEYWORD_PROCESSOR_STORE.get()

    for (packaging_str, _), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        packagings = packaging_str.split(";")

        for packaging in packagings:
            match_str = text[span_start:span_end]
            insights.append(
                {
                    "packaging_tag": get_tag(packaging),
                    "packaging": packaging,
                    "text": match_str,
                    "notify": True,
                    "automatic_processing": True,
                }
            )

    return insights
