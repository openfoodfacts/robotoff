from typing import Dict, List, Optional, Union

from robotoff.insights import InsightType
from robotoff.insights.dataclass import RawInsight
from robotoff.insights.ocr.dataclass import OCRResult


def get_image_lang(ocr_result: Union[OCRResult, str]) -> List[RawInsight]:
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
        RawInsight(
            type=InsightType.image_lang, data={"count": image_lang, "percent": percents}
        )
    ]
