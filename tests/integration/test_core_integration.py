import pytest

from robotoff.app.core import get_image_predictions

from .models_utils import ImageModelFactory, ImagePredictionFactory, clean_db


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    clean_db()
    # Run the test case.
    yield
    clean_db()


def test_get_image_predictions():
    image_prediction1 = ImagePredictionFactory(image__barcode="123")
    image_model1 = image_prediction1.image
    image_prediction2 = ImagePredictionFactory(image__barcode="456")
    image_model2 = image_prediction2.image
    logo_annotation = LogoAnnotation(type="label")

    # test with "barcode" filter

    image_model_data = get_images(barcode="123")
    image_model_items = [item.to_dict() for item in image_model_data]

    assert len(image_model_items) == 1
    assert image_model_items[0]["id"] == image_model3.id
    assert image_model_items[0]["barcode"] == "123"

    # test filter with "barcode" and "with_predictions=True"
    image_model_data = get_images(barcode="123", with_predictions=True)
    image_model_items = [item.to_dict() for item in image_model_data]
    image_model_items.sort(key=lambda d: d["id"])
    assert len(image_model_items) == 2
    assert image_model_items[0]["id"] == image_model1.id
    assert image_model_items[1]["id"] == image_model3.id

    # test filter with "with_predictions=True"
    image_model_data = get_images(with_predictions=True)
    image_model_items = [item.to_dict() for item in image_model_data]
    image_model_items.sort(key=lambda d: d["id"])
    assert len(image_model_items) == 3
    assert image_model_items[0]["id"] == image_model1.id
    assert image_model_items[1]["id"] == image_model2.id
    assert image_model_items[2]["id"] == image_model3.id

    # test filter with "barcode" and "with_predictions=True"
    image_model_data = get_images(barcode="456", with_predictions=True)
    image_model_items = [item.to_dict() for item in image_model_data]
    assert len(image_model_items) == 1
    assert image_model_items[0]["id"] == image_model2.id