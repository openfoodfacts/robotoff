import re
from typing import List, Dict, Optional, Union

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRRegex, OCRField, OCRResult, get_text
from robotoff.insights.ocr.utils import generate_keyword_processor
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore


def generate_trace_keyword_processor(labels: Optional[List[str]] = None):
    if labels is None:
        labels = list(text_file_iter(settings.OCR_TRACE_ALLERGEN_DATA_PATH))

    return generate_keyword_processor(labels)


TRACES_REGEX = OCRRegex(
    re.compile(
        r"(?:possibilit[ée] de traces|conditionné dans un atelier qui manipule|peut contenir(?: des traces)?|traces? [ée]ventuelles? d[e']|traces? d[e']|may contain)"
    ),
    field=OCRField.full_text_contiguous,
    lowercase=True,
)

TRACE_KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_trace_keyword_processor, expiration_interval=None
)


def find_traces(content: Union[OCRResult, str]) -> List[Dict]:
    insights = []

    text = get_text(content, TRACES_REGEX)

    if not text:
        return []

    processor = TRACE_KEYWORD_PROCESSOR_STORE.get()

    for match in TRACES_REGEX.regex.finditer(text):
        prompt = match.group()
        end_idx = match.end()
        captured = text[end_idx : end_idx + 100]

        for (trace_tag, trace), span_start, span_end in processor.extract_keywords(
            captured, span_info=True
        ):
            match_str = captured[span_start:span_end]
            insights.append(
                {
                    "trace_tag": trace_tag,
                    "text": match_str,
                    "prompt": prompt,
                    "notify": False,
                }
            )

    return insights
