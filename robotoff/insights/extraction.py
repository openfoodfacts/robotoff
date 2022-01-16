import pathlib
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests
from PIL import Image

from robotoff.insights import ocr
from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import ProductInsights, RawInsight
from robotoff.insights.ocr.core import get_barcode_from_path
from robotoff.insights.ocr.dataclass import OCRParsingException
from robotoff.prediction.object_detection import (
    ObjectDetectionModelRegistry,
    ObjectDetectionRawResult,
)
from robotoff.utils import get_image_from_url, get_logger, http_session

logger = get_logger(__name__)


DEFAULT_INSIGHT_TYPES: List[InsightType] = [
    InsightType.label,
    InsightType.packager_code,
    InsightType.product_weight,
    InsightType.image_flag,
    InsightType.expiration_date,
    InsightType.brand,
    InsightType.store,
    InsightType.packaging,
    InsightType.category,
]

IMAGE_IMPORT_INSIGHT_TYPES: List[InsightType] = [
    InsightType.label,
    InsightType.packager_code,
    InsightType.product_weight,
    InsightType.image_flag,
    InsightType.expiration_date,
    InsightType.brand,
    InsightType.store,
    InsightType.packaging,
    InsightType.nutrient,
    InsightType.nutrient_mention,
    InsightType.image_lang,
    InsightType.image_orientation,
    InsightType.category,
]


PRODUCT_NAME_INSIGHT_TYPES: List[InsightType] = [
    InsightType.label,
    InsightType.product_weight,
    InsightType.brand,
]


def get_insights_from_product_name(
    barcode: str, product_name: str
) -> Dict[InsightType, ProductInsights]:
    results = {}
    for insight_type in PRODUCT_NAME_INSIGHT_TYPES:
        insights = ocr.extract_insights(product_name, insight_type)

        if insights:
            for insight in insights:
                insight.data["source"] = "product_name"

            results[insight_type] = ProductInsights(
                insights=insights, barcode=barcode, type=insight_type,
            )

    return results


def get_insights_from_image(
    barcode: str, image_url: str, ocr_url: str
) -> Dict[InsightType, ProductInsights]:
    try:
        ocr_insights = extract_ocr_insights(ocr_url, IMAGE_IMPORT_INSIGHT_TYPES)
    except requests.exceptions.RequestException as e:
        logger.info("error during OCR JSON download", exc_info=e)
        return {}
    except OCRParsingException as e:
        logger.error("OCR JSON Parsing error", exc_info=e)
        return {}

    extract_nutriscore = has_nutriscore_insight(
        ocr_insights.get(InsightType.label, None)
    )
    image_ml_insights = extract_image_ml_insights(
        image_url, extract_nutriscore=extract_nutriscore
    )

    insight_types = set(ocr_insights.keys()).union(image_ml_insights.keys())

    results: Dict[InsightType, ProductInsights] = {}

    for insight_type in insight_types:
        product_insights: List[ProductInsights] = []

        if insight_type in ocr_insights:
            product_insights.append(ocr_insights[insight_type])

        if insight_type in image_ml_insights:
            product_insights.append(image_ml_insights[insight_type])

        results[insight_type] = ProductInsights.merge(product_insights)

    return results


def has_nutriscore_insight(label_insights: Optional[ProductInsights]) -> bool:
    if label_insights is None:
        return False

    for insight in label_insights.insights:
        if insight.value_tag == "en:nutriscore":
            return True

    return False


def get_source_from_image_url(image_url: str) -> str:
    image_url_path = urlparse(image_url).path

    if image_url_path.startswith("/images/products"):
        image_url_path = image_url_path[len("/images/products") :]

    return image_url_path


def get_source_from_ocr_url(ocr_url: str) -> str:
    url_path = urlparse(ocr_url).path

    if url_path.startswith("/images/products"):
        url_path = url_path[len("/images/products") :]

    if url_path.endswith(".json"):
        url_path = str(pathlib.Path(url_path).with_suffix(".jpg"))

    return url_path


def get_barcode_from_url(ocr_url: str) -> Optional[str]:
    url_path = urlparse(ocr_url).path
    return get_barcode_from_path(url_path)


def extract_image_ml_insights(
    image_url: str, extract_nutriscore: bool = True
) -> Dict[InsightType, ProductInsights]:
    barcode = get_barcode_from_url(image_url)
    if barcode is None:
        raise ValueError("cannot extract barcode from URL: {}".format(barcode))

    results: Dict[InsightType, ProductInsights] = {}

    if extract_nutriscore:
        image = get_image_from_url(image_url, error_raise=True, session=http_session)
        # Currently all of the automatic processing for the Nutri-Score grades has been
        # disabled due to a prediction quality issue.
        # Last automatic processing threshold was set to 0.9 - resulting in ~70% incorrect
        # detection.
        nutriscore_insight = extract_nutriscore_label(image, manual_threshold=0.5,)

        if not nutriscore_insight:
            return results

        source_image = get_source_from_image_url(image_url)
        results[InsightType.label] = ProductInsights(
            insights=[nutriscore_insight],
            barcode=barcode,
            source_image=source_image,
            type=InsightType.label,
        )

    return results


def extract_ocr_insights(
    ocr_url: str, insight_types: Iterable[InsightType]
) -> Dict[InsightType, ProductInsights]:
    source_image = get_source_from_ocr_url(ocr_url)
    barcode = get_barcode_from_url(ocr_url)

    if barcode is None:
        raise ValueError("cannot extract barcode fro URL: {}".format(ocr_url))

    ocr_result = get_ocr_result(ocr_url)

    if ocr_result is None:
        logger.info("Error during OCR extraction: {}".format(ocr_url))
        return {}

    results = {}

    for insight_type in insight_types:
        insights = ocr.extract_insights(ocr_result, insight_type)

        if insights:
            results[insight_type] = ProductInsights(
                barcode=barcode,
                insights=insights,
                source_image=source_image,
                type=insight_type,
            )

    return results


def get_ocr_result(ocr_url: str) -> Optional[ocr.OCRResult]:
    r = http_session.get(ocr_url)
    r.raise_for_status()

    ocr_data: Dict = r.json()
    return ocr.OCRResult.from_json(ocr_data)


NUTRISCORE_LABELS: Dict[str, str] = {
    "nutriscore-a": "en:nutriscore-grade-a",
    "nutriscore-b": "en:nutriscore-grade-b",
    "nutriscore-c": "en:nutriscore-grade-c",
    "nutriscore-d": "en:nutriscore-grade-d",
    "nutriscore-e": "en:nutriscore-grade-e",
}


def extract_nutriscore_label(
    image: Image.Image,
    manual_threshold: float,
    automatic_threshold: Optional[float] = None,
) -> Optional[RawInsight]:
    model = ObjectDetectionModelRegistry.get("nutriscore")
    raw_result = model.detect_from_image(image, output_image=False)
    results = raw_result.select(threshold=manual_threshold)

    if not results:
        return None

    if len(results) > 1:
        logger.warn("more than one nutriscore detected, discarding detections")
        return None

    result = results[0]
    score = result.score

    automatic_processing = False
    if automatic_threshold:
        automatic_processing = score >= automatic_threshold
    label_tag = NUTRISCORE_LABELS[result.label]

    return RawInsight(
        type=InsightType.label,
        value_tag=label_tag,
        automatic_processing=automatic_processing,
        data={
            "confidence": score,
            "bounding_box": result.bounding_box,
            "model": "nutriscore",
            "notify": True,
        },
    )


def predict_objects(
    barcode: str, image_url: str, server_domain: str
) -> Dict[str, ObjectDetectionRawResult]:
    image = get_image_from_url(image_url, error_raise=True, session=http_session)
    results: Dict[str, ObjectDetectionRawResult] = {}

    if image is None:
        logger.warning("Invalid image: {}".format(image_url))
        return results

    image.load()

    for model_name in ("universal-logo-detector",):
        model = ObjectDetectionModelRegistry.get(model_name)
        results[model_name] = model.detect_from_image(image, output_image=False)

    return results
