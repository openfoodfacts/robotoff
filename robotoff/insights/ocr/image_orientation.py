from typing import List, Dict, Union

from robotoff.insights.ocr.dataclass import OCRResult, ImageOrientation


def find_image_orientation(ocr_result: Union[OCRResult, str]) -> List[Dict]:
    if isinstance(ocr_result, str):
        return []

    orientation_result = ocr_result.get_orientation()

    if (
        orientation_result is None
        or orientation_result.orientation == ImageOrientation.up
    ):
        return []

    return [orientation_result.to_json()]
