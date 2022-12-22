import datetime
import operator
from typing import Optional

import cachetools
import elasticsearch
import numpy as np
from elasticsearch.helpers import scan as elasticsearch_scan

from robotoff import settings
from robotoff.elasticsearch import get_es_client
from robotoff.insights.importer import import_insights
from robotoff.logo_label_type import LogoLabelType
from robotoff.models import LogoAnnotation, LogoConfidenceThreshold, LogoEmbedding
from robotoff.prediction.types import Prediction
from robotoff.slack import NotifierFactory
from robotoff.types import ElasticSearchIndex, PredictionType
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


LOGO_TYPE_MAPPING: dict[str, PredictionType] = {
    "brand": PredictionType.brand,
    "label": PredictionType.label,
}

UNKNOWN_LABEL: LogoLabelType = ("UNKNOWN", None)


BoundingBoxType = tuple[float, float, float, float]


def load_resources():
    """Load and cache resources."""
    logger.info("Loading logo resources...")
    get_logo_confidence_thresholds()
    get_logo_annotations()


def compute_iou(box_1: BoundingBoxType, box_2: BoundingBoxType) -> float:
    """Compute the IoU (intersection over union) for two bounding boxes.

    The boxes are expected to have the following format:
    (y_min, x_min, y_max, x_max).
    """
    y_min_1, x_min_1, y_max_1, x_max_1 = box_1
    y_min_2, x_min_2, y_max_2, x_max_2 = box_2
    x_max = min(x_max_1, x_max_2)
    x_min = max(x_min_1, x_min_2)
    y_max = min(y_max_1, y_max_2)
    y_min = max(y_min_1, y_min_2)
    width_inter = max(0, x_max - x_min)
    height_inter = max(0, y_max - y_min)
    area_inter = width_inter * height_inter
    box_1_area = (x_max_1 - x_min_1) * (y_max_1 - y_min_1)
    box_2_area = (x_max_2 - x_min_2) * (y_max_2 - y_min_2)
    union_area = box_1_area + box_2_area - area_inter
    return area_inter / union_area


def filter_logos(
    logos: list[JSONType], score_threshold: float, iou_threshold: float = 0.95
) -> list[tuple[int, JSONType]]:
    """Select logos that don't intersect with each other
    (IoU < `iou_threshold`) and that have a confidence score above
    `score_threshold`.

    Return a list of (original_idx, logo) tuples.
    """
    filtered = []
    skip_indexes = set()
    for i in range(len(logos)):
        logo = logos[i]
        if i not in skip_indexes:
            for j in range(i + 1, len(logos)):
                if (
                    compute_iou(logo["bounding_box"], logos[j]["bounding_box"])
                    >= iou_threshold
                ):
                    # logos are sorted by descending confidence score, so we ignore
                    # j logo (logo with lower confidence score)
                    skip_indexes.add(j)

        if logo["score"] >= score_threshold:
            filtered.append((i, logo))

    return filtered


@cachetools.cached(cachetools.LRUCache(maxsize=1))
def get_logo_confidence_thresholds() -> dict[LogoLabelType, float]:
    thresholds = {}

    for item in LogoConfidenceThreshold.select().iterator():
        thresholds[(item.type, item.value)] = item.threshold

    return thresholds


def get_stored_logo_ids() -> set[int]:
    es_client = get_es_client()
    scan_iter = elasticsearch_scan(
        es_client,
        query={"query": {"match_all": {}}},
        index=ElasticSearchIndex.logo,
        source=False,
    )
    return set(int(item["_id"]) for item in scan_iter)


def add_logos_to_ann(logo_embeddings: list[LogoEmbedding]) -> None:
    """Index logo embeddings in Elasticsearch ANN index."""
    es_client = get_es_client()

    for logo_embedding in logo_embeddings:
        embedding = np.frombuffer(logo_embedding.embedding, dtype=np.float32)
        es_client.index(
            index=ElasticSearchIndex.logo,
            id=logo_embedding.logo_id,
            document={
                "embedding": embedding / np.linalg.norm(embedding),
            },
        )


def save_nearest_neighbors(logo_embeddings: list[LogoEmbedding]) -> None:
    """Save nearest neighbors of a batch of logo embedding."""
    es_client = get_es_client()

    for logo_embedding in logo_embeddings:
        results = knn_search(
            es_client, logo_embedding.embedding, settings.K_NEAREST_NEIGHBORS
        )
        results = [item for item in results if item[0] != logo_embedding.logo_id][
            : settings.K_NEAREST_NEIGHBORS
        ]

        if results:
            logo_ids, distances = zip(*results)
            logo_embedding.logo.nearest_neighbors = {
                "distances": distances,
                "logo_ids": logo_ids,
                "updated_at": datetime.datetime.utcnow().isoformat(),
            }
            logo_embedding.logo.save()


def knn_search(
    client: elasticsearch.Elasticsearch,
    embedding_bytes: bytes,
    k: int = settings.K_NEAREST_NEIGHBORS,
) -> list[tuple[int, float]]:
    embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
    knn_body = {
        "field": "embedding",
        "query_vector": embedding / np.linalg.norm(embedding),
        "k": k + 1,
        "num_candidates": k + 1,
    }

    results = client.search(
        index=ElasticSearchIndex.logo, knn=knn_body, source=False, size=k + 1
    )
    if hits := results["hits"]["hits"]:
        return [(int(hit["_id"]), 1.0 - hit["_score"]) for hit in hits]

    return []


@cachetools.cached(cachetools.LRUCache(maxsize=1))
def get_logo_annotations() -> dict[int, LogoLabelType]:
    annotations: dict[int, LogoLabelType] = {}

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


def predict_label(logo: LogoAnnotation) -> Optional[LogoLabelType]:
    probs = predict_proba(logo)

    if probs is None or not probs:
        return None

    return sorted(probs.items(), key=operator.itemgetter(0))[0][0]


def predict_proba(
    logo: LogoAnnotation, weights: str = "distance"
) -> Optional[dict[LogoLabelType, float]]:
    if logo.nearest_neighbors is None:
        return None

    nn_distances = logo.nearest_neighbors["distances"]
    nn_logo_ids = logo.nearest_neighbors["logo_ids"]

    logo_annotations = get_logo_annotations()

    nn_labels: list[LogoLabelType] = []
    for nn_logo_id in nn_logo_ids:
        nn_labels.append(logo_annotations.get(nn_logo_id, UNKNOWN_LABEL))

    return _predict_proba(nn_logo_ids, nn_labels, nn_distances, weights)


def _predict_proba(
    logo_ids: list[int],
    nn_labels: list[LogoLabelType],
    nn_distances: list[float],
    weights: str,
) -> dict[LogoLabelType, float]:
    weights = get_weights(np.array(nn_distances), weights)
    labels: list[LogoLabelType] = [UNKNOWN_LABEL] + [
        x for x in set(nn_labels) if x != UNKNOWN_LABEL
    ]
    label_to_id = {label: i for i, label in enumerate(labels)}
    proba_k = np.zeros(len(labels))
    pred_labels = np.array([label_to_id[x] for x in nn_labels])

    for i, idx in enumerate(pred_labels.T):
        proba_k[idx] += weights[i]

    proba_k /= proba_k.sum()

    prediction: dict[LogoLabelType, float] = {}
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
    logos: list[LogoAnnotation],
    server_domain: str,
    thresholds: dict[LogoLabelType, float],
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

    predictions = predict_logo_predictions(selected_logos, logo_probs)
    imported = import_insights(predictions, server_domain)

    for logo, probs in zip(selected_logos, logo_probs):
        NotifierFactory.get_notifier().send_logo_notification(logo, probs)

    return imported


def generate_insights_from_annotated_logos(
    logos: list[LogoAnnotation], server_domain: str
) -> int:
    predictions = []
    for logo in logos:
        prediction = generate_prediction(
            logo_type=logo.annotation_type,
            logo_value=logo.taxonomy_value,
            automatic_processing=True,  # because this is a user annotation, which we trust.
            data={
                "confidence": 1.0,
                "logo_id": logo.id,
                "bounding_box": logo.bounding_box,
                "username": logo.username,
                "is_annotation": True,  # it's worth restating it
            },
        )

        if prediction is None:
            continue

        image = logo.image_prediction.image
        prediction.barcode = image.barcode
        prediction.source_image = image.source_image
        predictions.append(prediction)

    imported = import_insights(predictions, server_domain)

    if imported:
        logger.info("%s logo insights imported after annotation", imported)
    return imported


def predict_logo_predictions(
    logos: list[LogoAnnotation], logo_probs: list[dict[LogoLabelType, float]]
) -> list[Prediction]:
    predictions = []

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
            logo_type=label[0],
            logo_value=label[1],
            data={
                "confidence": max_prob,
                "logo_id": logo.id,
                "bounding_box": logo.bounding_box,
            },
        )

        if prediction is not None:
            image = logo.image_prediction.image
            prediction.barcode = image.barcode
            prediction.source_image = image.source_image
            predictions.append(prediction)

    return predictions


def generate_prediction(
    logo_type: str,
    logo_value: Optional[str],
    data: dict,
    automatic_processing: Optional[bool] = False,
) -> Optional[Prediction]:
    """Generate a Prediction from a logo.

    The Prediction may either be created after the annotation of the logo by
    a human (in which case `automatic_processing` is True), or by infering the
    logo value from nearest neighbor labels (in which case
    `automatic_processing` is False).

    Currently, only brand and label logo types are supported: None is returned
    if the logo type is different, or if the logo_value is None.
    """
    if logo_type not in LOGO_TYPE_MAPPING or logo_value is None:
        return None

    prediction_type = LOGO_TYPE_MAPPING[logo_type]

    value_tag = None
    value = None

    if prediction_type == PredictionType.brand:
        value_tag = value = logo_value

    elif prediction_type == PredictionType.label:
        value_tag = logo_value

    return Prediction(
        type=prediction_type,
        value_tag=value_tag,
        value=value,
        automatic_processing=automatic_processing,
        predictor="universal-logo-detector",
        data=data,
    )
