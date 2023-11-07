from unittest.mock import MagicMock

import pytest

from robotoff.images import delete_images
from robotoff.models import (
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    LogoEmbedding,
    Prediction,
    ProductInsight,
)
from robotoff.off import generate_image_path
from robotoff.types import ProductIdentifier, ServerType

from .models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    LogoAnnotationFactory,
    LogoEmbeddingFactory,
    PredictionFactory,
    ProductInsightFactory,
    clean_db,
)

DEFAULT_SERVER_TYPE = ServerType.off


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        clean_db()
        # Run the test case.
    yield

    with peewee_db:
        clean_db()


def test_delete_images(peewee_db, mocker):
    mock_es_client = MagicMock()
    mocker.patch("robotoff.images.get_es_client", return_value=mock_es_client)
    mock_delete_ann_logos = mocker.patch("robotoff.images.delete_ann_logos")
    with peewee_db:
        barcode = "1"
        image_id = "1"
        product_id = ProductIdentifier(barcode, DEFAULT_SERVER_TYPE)
        source_image = generate_image_path(product_id, image_id)
        # to be deleted
        image_1 = ImageModelFactory(barcode=barcode, image_id=image_id)
        # to be kept (different image ID)
        image_2 = ImageModelFactory(barcode=barcode, image_id="2")
        # to be kept (different barcode)
        image_3 = ImageModelFactory(barcode="2", image_id=image_id)
        # to be kept (same barcode/image ID, but different server type)
        image_4 = ImageModelFactory(
            barcode=barcode, image_id=image_id, server_type="obf"
        )

        image_prediction_1 = ImagePredictionFactory(image=image_1)
        logo_annotation_1 = LogoAnnotationFactory(image_prediction=image_prediction_1)
        logo_embedding_1 = LogoEmbeddingFactory(logo=logo_annotation_1)

        # to be deleted
        prediction_1 = PredictionFactory(barcode=barcode, source_image=source_image)
        # to be kept (different barcode)
        prediction_2 = PredictionFactory(barcode="2")
        # to be kept (different server type)
        prediction_3 = PredictionFactory(
            barcode=barcode, server_type="obf", source_image=source_image
        )
        # to be deleted
        insight_1 = ProductInsightFactory(
            barcode=barcode, source_image=source_image, annotation=None
        )
        # to be kept
        insight_2 = ProductInsightFactory(
            barcode=barcode, source_image=source_image, annotation=1
        )
        # to be kept
        insight_3 = ProductInsightFactory(barcode="2", annotation=None)
        # to be kept (different server type)
        insight_4 = ProductInsightFactory(
            barcode="1", server_type="obf", source_image=source_image, annotation=None
        )
        delete_images(product_id, [image_id])

        assert ImageModel.get_or_none(id=image_1.id).deleted
        assert not ImageModel.get_or_none(id=image_2.id).deleted
        assert not ImageModel.get_or_none(id=image_3.id).deleted
        assert not ImageModel.get_or_none(id=image_4.id).deleted

        # the prediction associated with the image should be deleted
        assert Prediction.get_or_none(id=prediction_1.id) is None
        # but not the unrelated ones
        assert Prediction.get_or_none(id=prediction_2.id) is not None
        assert Prediction.get_or_none(id=prediction_3.id) is not None

        # the unannotated product insight associated with the image should be
        # deleted
        assert ProductInsight.get_or_none(id=insight_1.id) is None
        # but not the annotated one
        assert ProductInsight.get_or_none(id=insight_2.id) is not None
        # nor the ones unrelated to the deleted image
        assert ProductInsight.get_or_none(id=insight_3.id) is not None
        assert ProductInsight.get_or_none(id=insight_4.id) is not None

        # the image prediction is deleted as there are no annotated logos
        # associated with it
        assert ImagePrediction.get_or_none(id=image_prediction_1.id) is None
        # same for the logo annotation
        assert LogoAnnotation.get_or_none(id=logo_annotation_1.id) is None
        # check that the embedding is deleted
        assert LogoEmbedding.get_or_none(logo_id=logo_embedding_1.id) is None

    mock_delete_ann_logos.assert_called_once_with(
        mock_es_client, [logo_annotation_1.id]
    )
