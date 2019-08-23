from urllib.parse import urlparse

from typing import Optional, Dict, List

from PIL import Image

from robotoff.insights._enum import InsightType
from robotoff.insights import ocr
from robotoff.ml.object_detection import ObjectDetectionModelRegistry
from robotoff.off import http_session
from robotoff.utils import get_image_from_url, get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def get_insights_from_image(barcode: str, image_url: str, ocr_url: str) \
        -> Optional[Dict]:
    ocr_insights = extract_ocr_insights(ocr_url)

    extract_nutriscore = has_nutriscore_insight(ocr_insights)
    image_ml_insights = extract_image_ml_insights(
        image_url, extract_nutriscore=extract_nutriscore)

    insight_types = set(ocr_insights.keys()).union(image_ml_insights.keys())

    results = {}

    for insight_type in insight_types:
        insights = (ocr_insights.get(insight_type, []) +
                    image_ml_insights.get(insight_type, []))

        results[insight_type] = generate_insights_dict(insights,
                                                       barcode,
                                                       insight_type,
                                                       image_url)

    if not results:
        return None

    return results


def has_nutriscore_insight(insights: JSONType) -> bool:
    for insight in insights.get('label', []):
        if insight['label_tag'] == 'en:nutriscore':
            return True

    return False


def generate_insights_dict(insights: List[JSONType],
                           barcode: str,
                           insight_type: str,
                           image_url: str):
    image_url_path = urlparse(image_url).path

    if image_url_path.startswith('/images/products'):
        image_url_path = image_url_path[len("/images/products"):]

    return {
        'insights': insights,
        'barcode': barcode,
        'type': insight_type,
        'source': image_url_path,
    }


def extract_image_ml_insights(image_url: str,
                              extract_nutriscore: bool = True) -> JSONType:
    results: JSONType = {}

    if extract_nutriscore:
        image = get_image_from_url(image_url, error_raise=True, session=http_session)
        nutriscore_insight = extract_nutriscore_label(image,
                                                      manual_threshold=0.5,
                                                      automatic_threshold=0.9)

        if not nutriscore_insight:
            return results

        results = {
            'label': [
                nutriscore_insight
            ]
        }

    return results


def extract_ocr_insights(ocr_url: str) -> JSONType:
    r = http_session.get(ocr_url)

    if r.status_code == 404:
        logger.info("OCR JSON {} not found".format(ocr_url))
        return {}

    r.raise_for_status()

    ocr_data: Dict = r.json()
    ocr_result = ocr.OCRResult.from_json(ocr_data)

    if ocr_result is None:
        logger.info("Error during OCR extraction: {}".format(ocr_url))
        return {}

    results = {}

    for insight_type in (InsightType.label.name,
                         InsightType.packager_code.name,
                         InsightType.product_weight.name,
                         InsightType.image_flag.name,
                         InsightType.expiration_date.name,
                         InsightType.brand.name,
                         InsightType.store.name):
        insights = ocr.extract_insights(ocr_result, insight_type)

        if insights:
            results[insight_type] = insights

    return results


def extract_nutriscore_label(image: Image.Image,
                             manual_threshold: float,
                             automatic_threshold: float) -> Optional[JSONType]:
    model = ObjectDetectionModelRegistry.get('nutriscore')
    raw_result = model.detect_from_image(image, output_image=False)
    results = raw_result.select(threshold=manual_threshold)

    if not results:
        return None

    if len(results) > 1:
        logger.warn("more than one nutriscore detected, discarding detections")
        return None

    result = results[0]
    score = result.score

    automatic_processing = score >= automatic_threshold
    label_tag = 'en:{}'.format(result.label)

    return {
        'label_tag': label_tag,
        'notify': True,
        'automatic_processing': automatic_processing,
        'confidence': score,
        'bounding_box': result.bounding_box,
        'model': 'nutriscore',
    }
