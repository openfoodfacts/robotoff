import pytest

from robotoff.app.core import get_images, get_insights, get_images, get_predictions, get_image_predictions


from .models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    LogoAnnotationFactory,
    PredictionFactory,
    ProductInsightFactory,
    clean_db,
)


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    clean_db()
    # Run the test case.
    yield
    clean_db()


def prediction_ids(data):
    return {prediction.id for prediction in data}


def test_get_image_predictions():
    logo_annotation1 = LogoAnnotationFactory(image_prediction__image__barcode="123")
    image_prediction1 = logo_annotation1.image_prediction
    logo_annotation2 = LogoAnnotationFactory(
        image_prediction__image__barcode="456", image_prediction__type="label"
    )
    image_prediction2 = logo_annotation2.image_prediction
    image_prediction3 = ImagePredictionFactory(image__barcode="123", type="label")
    image_prediction4 = ImagePredictionFactory(image__barcode="123", type="category")

    # test with "barcode" filter
    data = list(get_image_predictions(barcode="123"))
    assert len(data) == 2
    assert prediction_ids(data) == {image_prediction3.id, image_prediction4.id}

    # test filter with "barcode" and "with_logo=True"
    data = list(get_image_predictions(barcode="123", with_logo=True))
    assert len(data) == 3
    assert prediction_ids(data) == {
        image_prediction1.id,
        image_prediction3.id,
        image_prediction4.id,
    }

    # test filter with "with_logo=True"
    data = list(get_image_predictions(with_logo=True))
    assert len(data) == 4  # we have them all

    # test filter with "type=label" and "with_logo=True"
    data = list(get_image_predictions(type="label", with_logo=True))
    assert len(data) == 2
    assert prediction_ids(data) == {image_prediction2.id, image_prediction3.id}

    # test filter with "type=label" and "with_logo=False"
    data = list(get_image_predictions(type="label", with_logo=False))
    assert len(data) == 1
    assert prediction_ids(data) == {image_prediction3.id}


def test_get_predictions():
    prediction1 = PredictionFactory(
        barcode="123", keep_types="category", value_tag="en:seeds"
    )
    prediction2 = PredictionFactory(
        barcode="123", keep_types="category", value_tag="en:beers"
    )
    prediction3 = PredictionFactory(
        barcode="123", keep_types="label", value_tag="en:eu-organic"
    )
    prediction4 = PredictionFactory(
        barcode="456", keep_types="label", value_tag="en:eu-organic"
    )

    actual_prediction1 = get_predictions(barcode="123")
    actual_items1 = [item.to_dict() for item in actual_prediction1]
    actual_items1.sort(key=lambda d: d["id"])
    assert len(actual_items1) == 3
    assert actual_items1[0]["id"] == prediction1.id
    assert actual_items1[0]["barcode"] == "123"
    assert actual_items1[0]["type"] == "category"
    assert actual_items1[0]["value_tag"] == "en:seeds"
    assert actual_items1[1]["value_tag"] == "en:beers"
    assert actual_items1[1]["id"] == prediction2.id
    assert actual_items1[2]["value_tag"] == "en:eu-organic"
    assert actual_items1[2]["id"] == prediction3.id

    # test that as we have no "brand" prediction, returned list is empty
    actual_prediction2 = get_predictions(keep_types=["brand"])
    assert list(actual_prediction2) == []

    # test that predictions are filtered based on "value_tag=en:eu-organic",
    # returns only "en:eu-organic" predictions
    actual_prediction3 = get_predictions(value_tag="en:eu-organic")
    actual_items3 = [item.to_dict() for item in actual_prediction3]
    actual_items3.sort(key=lambda d: d["id"])
    assert len(actual_items3) == 2
    assert actual_items3[0]["id"] == prediction3.id
    assert actual_items3[0]["barcode"] == "123"
    assert actual_items3[0]["type"] == "category"
    assert actual_items3[0]["value_tag"] == "en:eu-organic"
    assert actual_items3[1]["id"] == prediction4.id

    # test that we can filter "barcode", "value_tag", "keep_types" prediction
    actual_prediction4 = get_predictions(
        barcode="123", value_tag="en:eu-organic", keep_types=["category"]
    )
    actual_items4 = [item.to_dict() for item in actual_prediction4]
    assert actual_items4[0]["id"] == prediction3.id
    assert len(actual_items4) == 1

    # test to filter results with "label" and "category" prediction
    actual_prediction5 = get_predictions(keep_types=["label", "category"])
    actual_items5 = [item.to_dict() for item in actual_prediction5]
    assert len(actual_items5) == 4


def test_get_images():
    image_prediction1 = ImagePredictionFactory(image__barcode="123")
    image_model1 = image_prediction1.image
    image_prediction2 = ImagePredictionFactory(image__barcode="456")
    image_model2 = image_prediction2.image
    image_model3 = ImageModelFactory(barcode="123")

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


def test_get_unanswered_questions_list():
    product1 = ProductInsightFactory(type="category", value_tag="en:beer")
    insight_data1 = get_insights(keep_types=["category"])
    insight_data_items1 = [item.to_dict() for item in insight_data1]
    assert insight_data_items1[0]["id"] == product1.id
    # assert insight_data_items1[0]["type"] == []

    product2 = ProductInsightFactory(type="label", value_tag="en:apricots")
    insight_data2 = get_insights(keep_types=["label"], value_tag="en:apricots")
    insight_data_items2 = [item.to_dict() for item in insight_data2]
    assert insight_data_items2[0]["id"] == product2.id
    # assert insight_data_items2[0]["type"] == []

    product3 = ProductInsightFactory(type="label", value_tag="en:soups")
    insight_data3 = get_insights(keep_types=["label"], value_tag="en:soups")
    insight_data_items3 = [item.to_dict() for item in insight_data3]
    assert insight_data_items3[0]["id"] == product3.id
    # assert insight_data_items3[0]["type"] == []

    product4 = ProductInsightFactory(type="category", value_tag="en:chicken")
    insight_data4 = get_insights(keep_types=["category"], value_tag="en:chicken")
    insight_data_items4 = [item.to_dict() for item in insight_data4]
    assert insight_data_items4[0]["id"] == product4.id
    # assert insight_data_items4[0]["type"] == []

    insight_data5 = get_insights(keep_types=["category"])
    insight_data_items5 = [item.to_dict() for item in insight_data5]
    assert len(insight_data_items5) == 2
