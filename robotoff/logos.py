import operator
from typing import Dict, List, Optional, Tuple

import numpy as np

from robotoff import settings
from robotoff.models import ImageModel, LogoAnnotation
from robotoff.slack import post_message
from robotoff.utils import get_logger, http_session
from robotoff.utils.cache import CachedStore


logger = get_logger(__name__)


def add_logos_to_ann(image: ImageModel, logos: List[LogoAnnotation]) -> int:
    if not logos:
        return 0

    image_url = settings.OFF_IMAGE_BASE_URL + image.source_image

    data = {
        "image_url": image_url,
        "logos": [{"bounding_box": logo.bounding_box, "id": logo.id} for logo in logos],
    }
    r = http_session.post(
        "https://robotoff.openfoodfacts.org/api/v1/ann/add", json=data, timeout=30
    )

    if not r.ok:
        logger.warning(f"error while adding image to ANN ({r.status_code}): {r.text}")
        return 0

    return r.json()["added"]


def save_nearest_neighbors(logos: List[LogoAnnotation]) -> int:
    logo_ids_params = ",".join((str(logo.id) for logo in logos))
    r = http_session.get(
        f"https://robotoff.openfoodfacts.org/api/v1/ann/batch?logo_ids={logo_ids_params}",
        timeout=30,
    )

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


LogoLabelType = Tuple[str, Optional[str]]
UNKNOWN_LABEL: LogoLabelType = ("UNKNOWN", None)


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


def predict_logo_label(logo: LogoAnnotation):
    probs = predict_proba(logo)

    if not probs:
        return

    max_prob = max((prob for label, prob in probs.items() if label != UNKNOWN_LABEL))

    if max_prob < 0.1:
        return

    crop_url = logo.get_crop_image_url()
    prob_text = "\n".join(
        (f"{label[0]} - {label[1]}: {prob:.2g}" for label, prob in probs.items())
    )
    text = f"Logo prediction for {crop_url}:\n{prob_text}"
    post_message(text, settings.SLACK_OFF_ROBOTOFF_ALERT_CHANNEL)
