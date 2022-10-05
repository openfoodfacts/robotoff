from typing import List, Optional, Union

from robotoff import settings
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore
from robotoff.utils.text import get_tag

from .dataclass import OCRResult, get_text
from .utils import generate_keyword_processor


def generate_packaging_keyword_processor(packaging: Optional[List[str]] = None):
    p = (
        text_file_iter(settings.OCR_PACKAGING_DATA_PATH)
        if packaging is None
        else packaging
    )
    return generate_keyword_processor(p)


KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_packaging_keyword_processor, expiration_interval=None
)


def find_packaging(content: Union[OCRResult, str]) -> List[Prediction]:
    predictions = []

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
            predictions.append(
                Prediction(
                    type=PredictionType.packaging,
                    value_tag=get_tag(packaging),
                    value=packaging,
                    data={"text": match_str, "notify": False},
                    automatic_processing=True,
                )
            )

    return predictions
