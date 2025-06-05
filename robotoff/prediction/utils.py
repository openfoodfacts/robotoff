from robotoff.models import ImageModel, ImagePrediction, Prediction
from robotoff.prediction.ocr.image_lang import ImageLangDataType
from robotoff.types import ObjectDetectionModel, PredictionType


def get_image_rotation(source_image: str) -> int | None:
    """Return the image rotation of the image, by fetching the associated
    `image_orientation` prediction from the DB.

    The image orientation is represented by a rotation angle in degrees:
    - 0: upright
    - 90: left
    - 180: upside down
    - 270: right

    If no prediction is found, return None.

    :param source_image: the source image of the prediction
    :return: the rotation angle of the image, or None if no prediction is found
    """
    image_orientation_prediction = Prediction.get_or_none(
        Prediction.type == PredictionType.image_orientation,
        Prediction.source_image == source_image,
    )

    if image_orientation_prediction is None:
        return None

    return image_orientation_prediction.data["rotation"]


def get_image_lang(source_image: str) -> ImageLangDataType | None:
    """Return the name of the language detected in the image, by fetching the
    associated `image_lang` prediction from the DB.

    If no prediction is found, return None.

    :param source_image: the source image of the prediction
    :return: the name of the language detected in the image, or None if no prediction
        is found
    """
    image_lang_prediction = Prediction.get_or_none(
        Prediction.type == PredictionType.image_lang,
        Prediction.source_image == source_image,
    )

    if image_lang_prediction is None:
        return None

    return image_lang_prediction.data


def get_nutrition_table_prediction(
    source_image: str, threshold: float = 0.5
) -> list | None:
    """Return the nutrition table prediction associated with the image.

    :param source_image: the source image of the prediction
    :return: the nutrition table prediction associated with the image
    """
    image_prediction = (
        ImagePrediction.select()
        .join(ImageModel)
        .where(
            ImagePrediction.model_name == ObjectDetectionModel.nutrition_table.name,
            ImageModel.source_image == source_image,
        )
    ).get_or_none()

    if image_prediction is None:
        return None

    objects = image_prediction.data["objects"]
    return [obj for obj in objects if obj["score"] >= threshold]
