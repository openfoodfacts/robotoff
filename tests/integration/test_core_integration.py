import pytest

from robotoff.app.core import get_image_predictions

from .models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    LogoAnnotationFactory,
    clean_db,
)


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    clean_db()
    # Run the test case.
    yield
    clean_db()


def test_get_image_predictions():
    image_prediction1 = LogoAnnotationFactory(image_prediction__image__barcode="123")
    image_model1 = image_prediction1.image_prediction
    image_prediction2 = LogoAnnotationFactory(image_prediction__image__barcode="456")
    image_model2 = image_prediction2.image_prediction
    logo_annotation = LogoAnnotationFactory(type="label")

    # test with "barcode" filter

    image_model_data = get_image_predictions(barcode="123")
    image_model_items = [item.to_dict() for item in image_model_data]
    assert len(image_model_items) == 0

    # test filter with "barcode" and "with_predictions=True"
    image_model_data = get_image_predictions(barcode="123", with_logo=True)
    image_model_items = [item.to_dict() for item in image_model_data]
    image_model_items.sort(key=lambda d: d["id"])
    assert len(image_model_items) == 1
    assert image_model_items[0]["id"] == image_prediction1.id

    # test filter with "with_logo=True"
    image_model_data = get_image_predictions(with_logo=True)
    image_model_items = [item.to_dict() for item in image_model_data]
    image_model_items.sort(key=lambda d: d["id"])
    assert len(image_model_items) == 3
    assert image_model_items[0]["id"] == image_prediction1.id
    assert image_model_items[1]["id"] == image_prediction2.id
    assert image_model_items[2]["id"] == logo_annotation.id

    # test filter with "barcode" and "with_logo=True"
    image_model_data = get_image_predictions(barcode="456", with_logo=True)
    image_model_items = [item.to_dict() for item in image_model_data]
    assert len(image_model_items) == 1
    assert image_model_items[0]["id"] == image_prediction2.id

    # test filter with "type=label" and "with_logo=True"
    image_model_data = get_image_predictions(type="label", with_logo=True)
    image_model_items = [item.to_dict() for item in image_model_data]
    assert len(image_model_items) == 3

    # test filter with "type=insight"
    image_model_data = get_image_predictions(type="insight")
    image_model_items = [item.to_dict() for item in image_model_data]
    assert len(image_model_items) == 0

    # test filter with "type=label" and "with_logo=False"
    image_model_data = get_image_predictions(type="label", with_logo=False)
    image_model_items = [item.to_dict() for item in image_model_data]
    assert len(image_model_items) == 0
