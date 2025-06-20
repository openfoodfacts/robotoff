from typing import TypedDict, Union

from openfoodfacts.ocr import OCRResult

from robotoff.types import Prediction, PredictionType

# Increase version ID when introducing breaking change: changes for which we
# want old predictions to be removed in DB and replaced by newer ones
PREDICTOR_VERSION = "1"


class ImageLangDataType(TypedDict):
    count: dict[str, int]
    percent: dict[str, float]


def get_image_lang(ocr_result: Union[OCRResult, str]) -> list[Prediction]:
    if isinstance(ocr_result, str):
        return []

    image_lang = ocr_result.get_languages()

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
            predictor_version=PREDICTOR_VERSION,
        )
    ]
