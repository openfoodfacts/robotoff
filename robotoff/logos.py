import datetime
import operator
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from robotoff import settings
from robotoff.insights.annotate import InvalidInsight, is_automatically_processable
from robotoff.insights.importer import import_insights
from robotoff.logo_label_type import LogoLabelType
from robotoff.models import ImageModel, LogoAnnotation, LogoConfidenceThreshold
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions
from robotoff.slack import NotifierFactory
from robotoff.utils import get_logger, http_session
from robotoff.utils.cache import CachedStore

logger = get_logger(__name__)


LOGO_TYPE_MAPPING: Dict[str, PredictionType] = {
    "brand": PredictionType.brand,
    "label": PredictionType.label,
}

UNKNOWN_LABEL: LogoLabelType = ("UNKNOWN", None)


def get_logo_confidence_thresholds() -> Dict[LogoLabelType, float]:
    thresholds = {}

    for item in LogoConfidenceThreshold.select().iterator():
        thresholds[(item.type, item.value)] = item.threshold

    return thresholds


LOGO_CONFIDENCE_THRESHOLDS = CachedStore(
    get_logo_confidence_thresholds, expiration_interval=10
)


def get_stored_logo_ids() -> Set[int]:
    r = http_session.get(
        settings.BaseURLProvider().robotoff().get() + "/api/v1/ann/stored", timeout=30
    )

    if not r.ok:
        logger.warning(
            f"error while fetching stored logo IDs ({r.status_code}): {r.text}"
        )
        return set()

    return set(r.json()["stored"])


def add_logos_to_ann(image: ImageModel, logos: List[LogoAnnotation]) -> int:
    if not logos:
        return 0

    image_url = settings.OFF_IMAGE_BASE_URL + image.source_image

    data = {
        "image_url": image_url,
        "logos": [{"bounding_box": logo.bounding_box, "id": logo.id} for logo in logos],
    }
    r = http_session.post(
        settings.BaseURLProvider().robotoff().get() + "/api/v1/ann/add",
        json=data,
        timeout=30,
    )

    if not r.ok:
        logger.warning(f"error while adding image to ANN ({r.status_code}): {r.text}")
        return 0

    return r.json()["added"]


def save_nearest_neighbors(logos: List[LogoAnnotation]) -> int:
    logo_ids_params = ",".join((str(logo.id) for logo in logos))
    r = http_session.get(
        settings.BaseURLProvider().robotoff().get()
        + "/api/v1/ann/batch?logo_ids="
        + logo_ids_params,
        timeout=30,
    )

    r.raise_for_status()
    response = r.json()

    results = {int(key): value for key, value in response["results"].items()}

    logo_id_to_logo = {logo.id: logo for logo in logos}
    missing_logo_ids = set(logo_id_to_logo.keys()).difference(set(results.keys()))

    if missing_logo_ids:
        logger.warning(f"Missing logo IDs in response: {missing_logo_ids}")

    saved = 0
    for logo_id, logo_results in results.items():
        if logo_id in logo_id_to_logo:
            logo = logo_id_to_logo[logo_id]
            distances = [n["distance"] for n in logo_results]
            logo_ids = [n["logo_id"] for n in logo_results]
            logo.nearest_neighbors = {
                "distances": distances,
                "logo_ids": logo_ids,
            }
            logo.save()
            saved += 1

    return saved


def get_logo_annotations() -> Dict[int, LogoLabelType]:
    annotations: Dict[int, LogoLabelType] = {}

    for logo in (
        LogoAnnotation.select(
            LogoAnnotation.id,
            LogoAnnotation.annotation_type,
            LogoAnnotation.annotation_value,
            LogoAnnotation.taxonomy_value,
        )
        .where(LogoAnnotation.annotation_type.is_null(False))
        .iterator()
    ):
        if logo.annotation_value is None:
            annotations[logo.id] = (logo.annotation_type, None)
        elif logo.taxonomy_value is not None:
            annotations[logo.id] = (logo.annotation_type, logo.taxonomy_value)

    return annotations


LOGO_ANNOTATIONS_CACHE = CachedStore(get_logo_annotations, expiration_interval=1)


def predict_label(logo: LogoAnnotation) -> Optional[LogoLabelType]:
    probs = predict_proba(logo)

    if probs is None or not probs:
        return None

    return sorted(probs.items(), key=operator.itemgetter(0))[0][0]


def predict_proba(
    logo: LogoAnnotation, weights: str = "distance"
) -> Optional[Dict[LogoLabelType, float]]:
    if logo.nearest_neighbors is None:
        return None

    nn_distances = logo.nearest_neighbors["distances"]
    nn_logo_ids = logo.nearest_neighbors["logo_ids"]

    logo_annotations = LOGO_ANNOTATIONS_CACHE.get()

    nn_labels: List[LogoLabelType] = []
    for nn_logo_id in nn_logo_ids:
        nn_labels.append(logo_annotations.get(nn_logo_id, UNKNOWN_LABEL))

    return _predict_proba(nn_logo_ids, nn_labels, nn_distances, weights)


def _predict_proba(
    logo_ids: List[int],
    nn_labels: List[LogoLabelType],
    nn_distances: List[float],
    weights: str,
) -> Dict[LogoLabelType, float]:
    weights = get_weights(np.array(nn_distances), weights)
    labels: List[LogoLabelType] = [UNKNOWN_LABEL] + [
        x for x in set(nn_labels) if x != UNKNOWN_LABEL
    ]
    label_to_id = {label: i for i, label in enumerate(labels)}
    proba_k = np.zeros(len(labels))
    pred_labels = np.array([label_to_id[x] for x in nn_labels])

    for i, idx in enumerate(pred_labels.T):
        proba_k[idx] += weights[i]

    proba_k /= proba_k.sum()

    prediction: Dict[LogoLabelType, float] = {}
    for i in range(len(proba_k)):
        prediction[labels[i]] = float(proba_k[i])

    return prediction


def get_weights(dist: np.ndarray, weights: str = "uniform"):
    """Get the weights from an array of distances and a parameter ``weights``
    Parameters
    ----------
    dist : ndarray
        The input distances
    weights : {'uniform', 'distance' or a callable}
        The kind of weighting used
    Returns
    -------
    weights_arr : array of the same shape as ``dist``
    """
    if weights in (None, "uniform"):
        return np.ones_like(dist)

    elif weights == "distance":
        # if user attempts to classify a point that was zero distance from one
        # or more training points, those training points are weighted as 1.0
        # and the other points as 0.0
        with np.errstate(divide="ignore"):
            dist = 1.0 / dist
        inf_mask = np.isinf(dist)
        inf_row = np.any(inf_mask)
        dist[inf_row] = inf_mask[inf_row]
        return dist
    elif callable(weights):
        return weights(dist)
    else:
        raise ValueError(
            "weights not recognized: should be 'uniform', "
            "'distance', or a callable function"
        )


def import_logo_insights(
    logos: List[LogoAnnotation],
    server_domain: str,
    thresholds: Dict[LogoLabelType, float],
    default_threshold: float = 0.1,
):
    selected_logos = []
    logo_probs = []
    for logo in logos:
        probs = predict_proba(logo)

        if not probs:
            continue

        label, max_prob = max(
            ((label, prob) for label, prob in probs.items() if label != UNKNOWN_LABEL),
            default=(UNKNOWN_LABEL, 0.0),
            key=operator.itemgetter(1),
        )
        threshold = thresholds[label] if label in thresholds else default_threshold

        if label == UNKNOWN_LABEL or max_prob < threshold:
            continue

        selected_logos.append(logo)
        logo_probs.append(probs)

    product_predictions = predict_logo_predictions(selected_logos, logo_probs)
    imported = import_insights(product_predictions, server_domain, automatic=True)

    for logo, probs in zip(selected_logos, logo_probs):
        NotifierFactory.get_notifier().send_logo_notification(logo, probs)

    return imported


def generate_insights_from_annotated_logos(
    logos: List[LogoAnnotation], server_domain: str
):
    product_predictions: List[ProductPredictions] = []
    for logo in logos:
        prediction = generate_prediction(
            logo.annotation_type, logo.taxonomy_value, confidence=1.0, logo_id=logo.id
        )

        if prediction is None:
            return

        image = logo.image_prediction.image

        try:
            prediction.automatic_processing = is_automatically_processable(
                image.barcode, image.source_image, datetime.timedelta(days=30)
            )
        except InvalidInsight:
            return

        if prediction.automatic_processing:
            prediction.data["notify"] = True

        product_predictions.append(
            ProductPredictions(
                predictions=[prediction],
                type=prediction.type,
                barcode=image.barcode,
                source_image=image.source_image,
            )
        )

    imported = import_insights(product_predictions, server_domain, automatic=True)

    if imported:
        logger.info(f"{imported} logo insights imported after annotation")


def predict_logo_predictions(
    logos: List[LogoAnnotation],
    logo_probs: List[Dict[LogoLabelType, float]],
) -> List[ProductPredictions]:
    grouped_predictions: Dict[Tuple[str, str, PredictionType], List[Prediction]] = {}

    for logo, probs in zip(logos, logo_probs):
        if not probs:
            continue

        label, max_prob = max(
            ((label, prob) for label, prob in probs.items() if label != UNKNOWN_LABEL),
            default=(UNKNOWN_LABEL, 0.0),
            key=operator.itemgetter(1),
        )

        if label == UNKNOWN_LABEL:
            continue

        prediction = generate_prediction(
            label[0], label[1], confidence=max_prob, logo_id=logo.id
        )

        if prediction is not None:
            image = logo.image_prediction.image
            source_image = image.source_image
            barcode = image.barcode
            key = (barcode, source_image, prediction.type)
            grouped_predictions.setdefault(key, [])
            grouped_predictions[key].append(prediction)

    product_predictions: List[ProductPredictions] = []

    for (
        (barcode, source_image, prediction_type),
        predictions,
    ) in grouped_predictions.items():
        product_predictions.append(
            ProductPredictions(
                predictions=predictions,
                type=prediction_type,
                barcode=barcode,
                source_image=source_image,
            )
        )

    return product_predictions


def generate_prediction(
    logo_type: str, logo_value: Optional[str], **kwargs
) -> Optional[Prediction]:
    if logo_type not in LOGO_TYPE_MAPPING:
        return None

    prediction_type = LOGO_TYPE_MAPPING[logo_type]

    value_tag = None
    value = None

    if prediction_type == PredictionType.brand:
        value = logo_value
        if value is None:
            return None

    elif prediction_type == PredictionType.label:
        value_tag = logo_value
        if value_tag is None:
            return None

    return Prediction(
        type=prediction_type,
        value_tag=value_tag,
        value=value,
        automatic_processing=False,
        predictor="universal-logo-detector",
        data=kwargs,
    )
