import re
from typing import Optional, Union

from robotoff import settings
from robotoff.types import Prediction, PredictionType
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore

from .dataclass import OCRField, OCRRegex, OCRResult, get_match_bounding_box, get_text
from .utils import generate_keyword_processor


def generate_trace_keyword_processor(labels: Optional[list[str]] = None):
    if labels is None:
        labels = list(text_file_iter(settings.OCR_TRACE_ALLERGEN_DATA_PATH))

    return generate_keyword_processor(labels)


TRACES_REGEX = OCRRegex(
    re.compile(
        r"(?:possibilit[ée] de traces|conditionné dans un atelier qui manipule|peut contenir(?: des traces)?|traces? [ée]ventuelles? d[e']|traces? d[e']|may contain)",
        re.I,
    ),
    field=OCRField.full_text_contiguous,
)

TRACE_KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_trace_keyword_processor, expiration_interval=None
)


def find_traces(content: Union[OCRResult, str]) -> list[Prediction]:
    predictions = []

    text = get_text(content, TRACES_REGEX)

    if not text:
        return []

    processor = TRACE_KEYWORD_PROCESSOR_STORE.get()

    for match in TRACES_REGEX.regex.finditer(text):
        prompt = match.group()
        end_idx = match.end()
        captured = text[end_idx : end_idx + 100]

        for (trace_tag, _), span_start, span_end in processor.extract_keywords(
            captured, span_info=True
        ):
            match_str = captured[span_start:span_end]
            data = {"text": match_str, "prompt": prompt, "notify": False}
            if (
                bounding_box := get_match_bounding_box(
                    content, match.start(), match.end()
                )
            ) is not None:
                data["bounding_box_absolute"] = bounding_box

            predictions.append(
                Prediction(
                    type=PredictionType.trace,
                    value_tag=trace_tag,
                    data=data,
                )
            )

    return predictions
