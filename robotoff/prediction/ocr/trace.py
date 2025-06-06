import re
from functools import cache
from typing import Union

from openfoodfacts.ocr import (
    OCRField,
    OCRRegex,
    OCRResult,
    get_match_bounding_box,
    get_text,
)

from robotoff import settings
from robotoff.types import Prediction, PredictionType
from robotoff.utils import text_file_iter
from robotoff.utils.text.flashtext import KeywordProcessor

from .utils import generate_keyword_processor

# Increase version ID when introducing breaking change: changes for which we
# want old predictions to be removed in DB and replaced by newer ones
PREDICTOR_VERSION = "1"


@cache
def generate_trace_keyword_processor(
    labels: list[str] | None = None,
) -> KeywordProcessor:
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


def find_traces(content: Union[OCRResult, str]) -> list[Prediction]:
    predictions = []

    text = get_text(content, TRACES_REGEX)

    if not text:
        return []

    processor = generate_trace_keyword_processor()

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
                    predictor="regex",
                    predictor_version=PREDICTOR_VERSION,
                )
            )

    return predictions
