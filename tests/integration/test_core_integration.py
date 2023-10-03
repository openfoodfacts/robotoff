import pytest
from openfoodfacts.types import Country

from robotoff.app.core import (
    get_image_predictions,
    get_images,
    get_insights,
    get_logo_annotation,
    get_predictions,
)
from robotoff.types import ServerType

from .models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    LogoAnnotationFactory,
    PredictionFactory,
    ProductInsightFactory,
    clean_db,
)

DEFAULT_SERVER_TYPE = ServerType.off


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
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
    data = list(get_image_predictions(DEFAULT_SERVER_TYPE, barcode="123"))
    assert len(data) == 2
    assert prediction_ids(data) == {image_prediction3.id, image_prediction4.id}

    # test filter with "barcode" and "with_logo=True"
    data = list(
        get_image_predictions(DEFAULT_SERVER_TYPE, barcode="123", with_logo=True)
    )
    assert len(data) == 3
    assert prediction_ids(data) == {
        image_prediction1.id,
        image_prediction3.id,
        image_prediction4.id,
    }

    # test filter with "with_logo=True"
    data = list(get_image_predictions(DEFAULT_SERVER_TYPE, with_logo=True))
    assert len(data) == 4  # we have them all

    # test filter with "type=label" and "with_logo=True"
    data = list(
        get_image_predictions(DEFAULT_SERVER_TYPE, type="label", with_logo=True)
    )
    assert len(data) == 2
    assert prediction_ids(data) == {image_prediction2.id, image_prediction3.id}

    # test filter with "type=label" and "with_logo=False"
    data = list(
        get_image_predictions(DEFAULT_SERVER_TYPE, type="label", with_logo=False)
    )
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

    actual_prediction1 = get_predictions(DEFAULT_SERVER_TYPE, barcode="123")
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
    actual_prediction2 = get_predictions(DEFAULT_SERVER_TYPE, keep_types=["brand"])
    assert list(actual_prediction2) == []

    # test that predictions are filtered based on "value_tag=en:eu-organic",
    # returns only "en:eu-organic" predictions
    actual_prediction3 = get_predictions(DEFAULT_SERVER_TYPE, value_tag="en:eu-organic")
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
        DEFAULT_SERVER_TYPE,
        barcode="123",
        value_tag="en:eu-organic",
        keep_types=["category"],
    )
    actual_items4 = [item.to_dict() for item in actual_prediction4]
    assert actual_items4[0]["id"] == prediction3.id
    assert len(actual_items4) == 1

    # test to filter results with "label" and "category" prediction
    actual_prediction5 = get_predictions(
        DEFAULT_SERVER_TYPE, keep_types=["label", "category"]
    )
    actual_items5 = [item.to_dict() for item in actual_prediction5]
    assert len(actual_items5) == 4


def test_get_images():
    image_prediction1 = ImagePredictionFactory(image__barcode="123")
    image_model1 = image_prediction1.image
    image_prediction2 = ImagePredictionFactory(image__barcode="456")
    image_model2 = image_prediction2.image
    image_model3 = ImageModelFactory(barcode="123")

    # test with "barcode" filter

    image_model_data = get_images(barcode="123", server_type=DEFAULT_SERVER_TYPE)
    image_model_items = [item.to_dict() for item in image_model_data]

    assert len(image_model_items) == 1
    assert image_model_items[0]["id"] == image_model3.id
    assert image_model_items[0]["barcode"] == "123"

    # test filter with "barcode" and "with_predictions=True"
    image_model_data = get_images(
        barcode="123", with_predictions=True, server_type=DEFAULT_SERVER_TYPE
    )
    image_model_items = [item.to_dict() for item in image_model_data]
    image_model_items.sort(key=lambda d: d["id"])
    assert len(image_model_items) == 2
    assert image_model_items[0]["id"] == image_model1.id
    assert image_model_items[1]["id"] == image_model3.id

    # test filter with "with_predictions=True"
    image_model_data = get_images(
        with_predictions=True, server_type=DEFAULT_SERVER_TYPE
    )
    image_model_items = [item.to_dict() for item in image_model_data]
    image_model_items.sort(key=lambda d: d["id"])
    assert len(image_model_items) == 3
    assert image_model_items[0]["id"] == image_model1.id
    assert image_model_items[1]["id"] == image_model2.id
    assert image_model_items[2]["id"] == image_model3.id

    # test filter with "barcode" and "with_predictions=True"
    image_model_data = get_images(
        barcode="456", with_predictions=True, server_type=DEFAULT_SERVER_TYPE
    )
    image_model_items = [item.to_dict() for item in image_model_data]
    assert len(image_model_items) == 1
    assert image_model_items[0]["id"] == image_model2.id


def test_get_unanswered_questions_list():
    product1 = ProductInsightFactory(type="category", value_tag="en:beer")
    insight_data1 = get_insights(keep_types=["category"])
    insight_data_items1 = [item.to_dict() for item in insight_data1]
    assert insight_data_items1[0]["id"] == product1.id

    product2 = ProductInsightFactory(type="label", value_tag="en:apricots")
    insight_data2 = get_insights(keep_types=["label"], value_tag="en:apricots")
    insight_data_items2 = [item.to_dict() for item in insight_data2]
    assert insight_data_items2[0]["id"] == product2.id

    product3 = ProductInsightFactory(type="label", value_tag="en:soups")
    insight_data3 = get_insights(keep_types=["label"], value_tag="en:soups")
    insight_data_items3 = [item.to_dict() for item in insight_data3]
    assert insight_data_items3[0]["id"] == product3.id

    product4 = ProductInsightFactory(type="category", value_tag="en:chicken")
    insight_data4 = get_insights(keep_types=["category"], value_tag="en:chicken")
    insight_data_items4 = [item.to_dict() for item in insight_data4]
    assert insight_data_items4[0]["id"] == product4.id

    insight_data5 = get_insights(keep_types=["category"])
    insight_data_items5 = [item.to_dict() for item in insight_data5]
    assert len(insight_data_items5) == 2

    product6 = ProductInsightFactory(value_tag="en:raisins", countries="en:india")
    insight_data6 = get_insights(countries=[Country["in"]])
    insight_data_items6 = [item.to_dict() for item in insight_data6]
    assert insight_data_items6[0]["id"] == product6.id
    assert insight_data_items6[0]["value_tag"] == "en:raisins"
    assert insight_data_items6[0]["countries"] == "en:india"


def test_get_logo_annotation():
    annotation_123 = LogoAnnotationFactory(
        barcode="123",
        image_prediction__image__barcode="123",
        annotation_value_tag="etorki",
        annotation_type="brand",
    )

    annotation_789 = LogoAnnotationFactory(
        barcode="789",
        image_prediction__image__barcode="789",
        annotation_value_tag="creme",
        annotation_type="dairies",
    )

    annotation_295 = LogoAnnotationFactory(
        barcode="295",
        image_prediction__image__barcode="295",
        annotation_value_tag="cheese",
        annotation_type="dairies",
    )

    annotation_396 = LogoAnnotationFactory(
        barcode="396",
        image_prediction__image__barcode="396",
        annotation_type="label",
    )

    LogoAnnotationFactory(
        barcode="306",
        image_prediction__image__barcode="306",
        annotation_value_tag="yoghurt",
        annotation_type="dairies",
    )

    # tests for "barcode"

    annotation_data = get_logo_annotation(DEFAULT_SERVER_TYPE, barcode="123")
    annotation_data_items = [item.to_dict() for item in annotation_data]
    assert annotation_data_items[0]["id"] == annotation_123.id
    assert annotation_data_items[0]["image_prediction"]["image"]["barcode"] == "123"
    assert annotation_data_items[0]["annotation_type"] == "brand"

    annotation_data = get_logo_annotation(DEFAULT_SERVER_TYPE, barcode="789")
    annotation_data_items = [item.to_dict() for item in annotation_data]
    assert annotation_data_items[0]["id"] == annotation_789.id
    assert annotation_data_items[0]["image_prediction"]["image"]["barcode"] == "789"
    assert annotation_data_items[0]["annotation_type"] == "dairies"

    annotation_data = get_logo_annotation(DEFAULT_SERVER_TYPE, barcode="396")
    annotation_data_items = [item.to_dict() for item in annotation_data]
    assert annotation_data_items[0]["id"] == annotation_396.id
    assert annotation_data_items[0]["image_prediction"]["image"]["barcode"] == "396"
    assert annotation_data_items[0]["annotation_type"] == "label"

    # test for "keep_types"

    annotation_data = get_logo_annotation(DEFAULT_SERVER_TYPE, keep_types=["dairies"])
    annotation_data_items = [item.to_dict() for item in annotation_data]
    annotation_data_items.sort(key=lambda d: d["id"])
    assert annotation_data_items[0]["annotation_type"] == "dairies"
    assert annotation_data_items[1]["annotation_type"] == "dairies"
    assert annotation_data_items[2]["annotation_type"] == "dairies"

    # tests for "value_tag"

    annotation_data = get_logo_annotation(DEFAULT_SERVER_TYPE, value_tag="cheese")
    annotation_data_items = [item.to_dict() for item in annotation_data]
    assert annotation_data_items[0]["id"] == annotation_295.id
    assert annotation_data_items[0]["annotation_value_tag"] == "cheese"
    assert annotation_data_items[0]["image_prediction"]["image"]["barcode"] == "295"
    assert annotation_data_items[0]["annotation_type"] == "dairies"
