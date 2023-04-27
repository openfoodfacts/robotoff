from typing import Union

from robotoff.types import Prediction, PredictionType

from .dataclass import ImageOrientation, OCRResult

# Increase version ID when introducing breaking change: changes for which we want
# old predictions to be removed in DB and replaced by newer ones
PREDICTOR_VERSION = "1"


def get_rotation_angle_from_orientation(image_orientation: ImageOrientation) -> int:
    if image_orientation == ImageOrientation.up:
        return 0
    elif image_orientation == ImageOrientation.unknown:
        return 0
    elif image_orientation == ImageOrientation.left:
        return 90
    elif image_orientation == ImageOrientation.right:
        return 270
    elif image_orientation == ImageOrientation.down:
        return 180
    else:
        raise ValueError("unknown image orientation: {}".format(image_orientation))


def find_image_orientation(ocr_result: Union[OCRResult, str]) -> list[Prediction]:
    if isinstance(ocr_result, str):
        return []

    orientation_result = ocr_result.get_orientation()

    if orientation_result is None:
        return []

    prediction = orientation_result.to_json()
    prediction["rotation"] = get_rotation_angle_from_orientation(
        orientation_result.orientation
    )
    return [
        Prediction(
            type=PredictionType.image_orientation,
            data=prediction,
            predictor_version=PREDICTOR_VERSION,
        )
    ]
