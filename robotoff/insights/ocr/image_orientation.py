from typing import Dict, List

from robotoff.insights.ocr.dataclass import ImageOrientation, OCRResult


def find_image_orientation(ocr_result: OCRResult) -> List[Dict]:
    orientation_result = ocr_result.get_orientation()

    if (
        orientation_result is None
        or orientation_result.orientation == ImageOrientation.up
    ):
        return []

    return [orientation_result.to_json()]
