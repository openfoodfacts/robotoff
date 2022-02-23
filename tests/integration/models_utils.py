"""Some factories for easy creation of models

we use https://github.com/cam-stitt/factory_boy-peewee,
although archived, this is lightweight, and should be easy to maintain if needed
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List

import factory
from factory_peewee import PeeweeModelFactory

from robotoff import settings
from robotoff.models import (
    AnnotationVote,
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    LogoConfidenceThreshold,
    Prediction,
    ProductInsight,
)


class UuidSequencer:
    """A mixin for factory of models that use a uuid as pk"""

    @classmethod
    def _setup_next_sequence(cls):
        # we can't rely on id for sequence, us a count
        model = cls._meta.model
        return model.select().count() + 1


class ProductInsightFactory(UuidSequencer, PeeweeModelFactory):
    class Meta:
        model = ProductInsight

    id = factory.LazyFunction(uuid.uuid4)  # type: ignore
    barcode = factory.Sequence(lambda n: f"{n:013}")
    type = "category"
    data: Dict[str, Any] = {}
    timestamp: datetime = factory.LazyFunction(datetime.utcnow)
    countries = ["en:france"]
    brands: List[str] = []
    n_votes = 0
    value_tag = "en:seeds"
    # we uses a lazy function for settings can change in a test
    server_domain: str = factory.LazyFunction(lambda: settings.OFF_SERVER_DOMAIN)
    server_type = "off"
    unique_scans_n = 10


class PredictionFactory(PeeweeModelFactory):
    class Meta:
        model = Prediction

    barcode = factory.Sequence(lambda n: f"{n:013}")
    type = "category"
    data: Dict[str, Any] = {}
    timestamp = factory.LazyFunction(datetime.now)
    value_tag = "en:seeds"
    server_domain = factory.LazyFunction(lambda: settings.OFF_SERVER_DOMAIN)


class AnnotationVoteFactory(UuidSequencer, PeeweeModelFactory):
    class Meta:
        model = AnnotationVote

    id = factory.LazyFunction(uuid.uuid4)
    # The insight this vote belongs to.
    insight_id = factory.SubFactory(ProductInsightFactory)
    value = 1
    device_id = factory.Sequence(lambda n: f"device-{n:02}")
    timestamp = factory.LazyFunction(datetime.utcnow)


class ImageModelFactory(PeeweeModelFactory):
    class Meta:
        model = ImageModel

    barcode = factory.Sequence(lambda n: f"{n:013}")
    uploaded_at = factory.LazyFunction(datetime.utcnow)
    image_id = factory.Sequence(lambda n: f"image-{n:02}")
    source_image = factory.Sequence(lambda n: f"/images/{n:02}.jpg")
    width = 400
    height = 400
    server_domain = factory.LazyFunction(lambda: settings.OFF_SERVER_DOMAIN)
    server_type = "off"


class ImagePredictionFactory(PeeweeModelFactory):
    class Meta:
        model = ImagePrediction

    type = "object_detection"
    model_name = "universal-logo-detector"
    model_version = "tf-universal-logo-detector-1.0"
    data = {
        "objects": [
            {"label": "brand", "score": 0.2, "bounding_box": [0.4, 0.4, 0.6, 0.6]}
        ]
    }
    timestamp = factory.LazyFunction(datetime.utcnow)
    image = factory.SubFactory(ImageModelFactory)


class LogoAnnotationFactory(PeeweeModelFactory):
    class Meta:
        model = LogoAnnotation

    image_prediction = factory.SubFactory(ImagePredictionFactory)
    index = 0
    bounding_box = [0.4, 0.4, 0.6, 0.6]
    score = 0.7
    annotation_value = "ab agriculture biologique"
    annotation_value_tag = "ab-agriculture-biologique"
    taxonomy_value = "en:ab-agriculture-biologique"
    annotation_type = "label"
    nearest_neighbors = {"logo_ids": [111111, 222222], "distances": [11.1, 12.4]}


class LogoConfidenceThresholdFactory(PeeweeModelFactory):
    class Meta:
        model = LogoConfidenceThreshold

    threshold = 0.7


def clean_db():
    # remove all models
    for model in (
        AnnotationVote,
        ImageModel,
        ImagePrediction,
        LogoAnnotation,
        LogoConfidenceThreshold,
        Prediction,
        ProductInsight,
    ):
        model.delete()
