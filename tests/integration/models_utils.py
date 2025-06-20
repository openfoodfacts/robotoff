"""Some factories for easy creation of models

We use https://github.com/cam-stitt/factory_boy-peewee,
although archived, this is lightweight, and should be easy to maintain or
replace if needed
"""

import uuid
from datetime import datetime
from typing import Any

import factory
import numpy as np
from factory_peewee import PeeweeModelFactory

from robotoff import models
from robotoff.models import (
    AnnotationVote,
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    LogoConfidenceThreshold,
    LogoEmbedding,
    Prediction,
    ProductInsight,
)
from robotoff.off import generate_image_path
from robotoff.types import ProductIdentifier, ServerType


class UuidSequencer:
    """A mixin for factory of models that use a uuid as pk"""

    @classmethod
    def _setup_next_sequence(cls):
        # we can't rely on id for sequence, thus a count
        model = cls._meta.model
        return model.select().count() + 1


class ProductInsightFactory(UuidSequencer, PeeweeModelFactory):
    class Meta:
        model = ProductInsight

    id = factory.LazyFunction(uuid.uuid4)  # type: ignore
    barcode = factory.Sequence(lambda n: f"{n:013}")
    type = "category"
    data: dict[str, Any] = {}
    timestamp: datetime = factory.LazyFunction(datetime.utcnow)  # type: ignore
    countries = ["en:france"]
    brands: list[str] = []
    n_votes = 0
    value_tag = "en:seeds"
    server_type = "off"
    unique_scans_n = 10
    annotation = None
    automatic_processing = False
    confidence: float | None = None
    predictor: str | None = None
    predictor_version: str | None = None
    bounding_box: list[float] | None = None
    lc: list[str] | None = None


class PredictionFactory(PeeweeModelFactory):
    class Meta:
        model = Prediction

    barcode = factory.Sequence(lambda n: f"{n:013}")
    type = "category"
    data: dict[str, Any] = {}
    timestamp = factory.LazyFunction(datetime.utcnow)
    value_tag = "en:seeds"
    automatic_processing = None
    predictor: str | None = None
    predictor_version: str | None = None
    confidence: float | None = None
    server_type: str = "off"
    source_image = factory.LazyAttribute(
        lambda o: generate_image_path(
            ProductIdentifier(o.barcode, ServerType[o.server_type]), "1"
        )
    )


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
    image_id = factory.Sequence(lambda n: f"{n:02}")
    source_image = factory.LazyAttribute(
        lambda o: generate_image_path(
            ProductIdentifier(o.barcode, ServerType[o.server_type]), o.image_id
        )
    )
    width = 400
    height = 400
    server_type = "off"


class ImagePredictionFactory(PeeweeModelFactory):
    class Meta:
        model = ImagePrediction

    type = "object_detection"
    model_name = "universal_logo_detector"
    model_version = "tf-universal-logo-detector-1.0"
    data = {
        "objects": [
            {"label": "brand", "score": 0.2, "bounding_box": [0.4, 0.4, 0.6, 0.6]}
        ]
    }
    timestamp = factory.LazyFunction(datetime.utcnow)
    image = factory.SubFactory(ImageModelFactory)
    max_confidence = 0.9


class LogoAnnotationFactory(PeeweeModelFactory):
    class Meta:
        model = LogoAnnotation

    image_prediction = factory.SubFactory(ImagePredictionFactory)
    index = 0
    bounding_box = [0.4, 0.4, 0.6, 0.6]
    score = 0.7
    annotation_value = "ab agriculture biologique"
    annotation_value_tag = "ab-agriculture-biologique"
    taxonomy_value = "fr:ab-agriculture-biologique"
    annotation_type = "label"
    nearest_neighbors = {"logo_ids": [111111, 222222], "distances": [11.1, 12.4]}
    barcode = factory.Sequence(lambda n: f"{n:013}")
    source_image = factory.Sequence(lambda n: f"/images/{n:02}.jpg")


class LogoConfidenceThresholdFactory(PeeweeModelFactory):
    class Meta:
        model = LogoConfidenceThreshold

    threshold = 0.7


class LogoEmbeddingFactory(PeeweeModelFactory):
    class Meta:
        model = LogoEmbedding

    logo = factory.SubFactory(LogoAnnotation)
    embedding = factory.LazyFunction(lambda: np.random.rand(512).tobytes())


def clean_db():
    print("DEBUG: Before cleaning: ", models.db.get_tables())
    # remove all models
    for model in (
        AnnotationVote,
        LogoAnnotation,
        ImagePrediction,
        ImageModel,
        LogoConfidenceThreshold,
        LogoEmbedding,
        Prediction,
        ProductInsight,
    ):
        model.delete().execute()
    print("DEBUG: After cleaning: ", models.db.get_tables())
