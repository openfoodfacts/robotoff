import functools
from typing import Optional, Union

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.types import Prediction, PredictionType
from robotoff.utils import text_file_iter

from .dataclass import OCRResult, SafeSearchAnnotationLikelihood, get_text

LABELS_TO_FLAG = {
    "Face",
    "Head",
    "Selfie",
    "Hair",
    "Forehead",
    "Chin",
    "Cheek",
    "Arm",
    "Tooth",
    "Human Leg",
    "Ankle",
    "Eyebrow",
    "Ear",
    "Neck",
    "Jaw",
    "Nose",
    "Facial Expression",
    "Glasses",
    "Eyewear",
    # Gesture generate too many false positive
    # "Gesture",
    # Thumb is pretty common on OFF images (as products are often hold in
    # hands)
    # "Thumb",
    "Jeans",
    "Shoe",
    "Child",
    "Baby",
    "Human",
    "Dog",
    "Cat",
    "Computer",
    "Laptop",
    "Refrigerator",
    "Cat",  # https://world.openfoodfacts.org/images/products/761/002/911/3600/1.json
}


@functools.cache
def generate_image_flag_keyword_processor() -> KeywordProcessor:
    processor = KeywordProcessor()

    for key, file_path in (
        ("beauty", settings.OCR_IMAGE_FLAG_BEAUTY_PATH),
        ("miscellaneous", settings.OCR_IMAGE_FLAG_MISCELLANEOUS_PATH),
    ):
        for name in text_file_iter(file_path):
            processor.add_keyword(name, clean_name=(name, key))

    return processor


def extract_image_flag_flashtext(
    processor: KeywordProcessor, text: str
) -> Optional[Prediction]:
    for (_, key), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        match_str = text[span_start:span_end]
        return Prediction(
            type=PredictionType.image_flag,
            data={"text": match_str, "type": "text", "label": key},
        )

    return None


def flag_image(content: Union[OCRResult, str]) -> list[Prediction]:
    predictions: list[Prediction] = []

    text = get_text(content)
    processor = generate_image_flag_keyword_processor()
    prediction = extract_image_flag_flashtext(processor, text)

    if prediction is not None:
        predictions.append(prediction)

    if isinstance(content, str):
        return predictions

    safe_search_annotation = content.get_safe_search_annotation()
    label_annotations = content.get_label_annotations()

    if safe_search_annotation:
        for key in ("adult", "violence"):
            value: SafeSearchAnnotationLikelihood = getattr(safe_search_annotation, key)
            if value >= SafeSearchAnnotationLikelihood.VERY_LIKELY:
                predictions.append(
                    Prediction(
                        type=PredictionType.image_flag,
                        data={
                            "type": "safe_search_annotation",
                            "label": key,
                            "likelihood": value.name,
                        },
                    )
                )

    for label_annotation in label_annotations:
        if (
            label_annotation.description in LABELS_TO_FLAG
            and label_annotation.score >= 0.6
        ):
            predictions.append(
                Prediction(
                    type=PredictionType.image_flag,
                    data={
                        "type": "label_annotation",
                        "label": label_annotation.description.lower(),
                        "likelihood": label_annotation.score,
                    },
                )
            )
            break

    return predictions
