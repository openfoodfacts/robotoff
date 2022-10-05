from typing import Dict, List, Optional, Union

from robotoff.prediction.types import Prediction, PredictionType

from .dataclass import OCRResult


def get_image_lang(ocr_result: Union[OCRResult, str]) -> List[Prediction]:
    if isinstance(ocr_result, str):
        return []

    image_lang: Optional[Dict[str, int]] = ocr_result.get_languages()

    if image_lang is None:
        return []

    words = image_lang["words"]
    percents = {}
    for key, count in image_lang.items():
        if key == "words":
            continue

        percents[key] = count * 100 / words

    return [
        Prediction(
            type=PredictionType.image_lang,
            data={"count": image_lang, "percent": percents},
        )
    ]
