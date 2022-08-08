import pytest

from robotoff.products import Product
from tests.integration.models_utils import (
    PredictionFactory,
    ProductInsightFactory,
    clean_db,
)

barcode1 = "00001"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    clean_db()
    # Run the test case.
    yield
    clean_db()


def fake_product_store():
    return {barcode1: Product({"labels_tags": ["en:nutriscore"]})}


def test_import_insights(mocker, monkeypatch):
    predictions_all = [
        PredictionFactory(
            type="label",
            barcode="3302740030949",
            data={
                "model": "nutriscore",
                "confidence": 0.871872,
                "bounding_box": [1441.3848, 1036.8024, 1685.6928, 1430.2488],
            },
            value_tag="en:nutriscore-c",
            value="",
            automatic_processing="f",
        ),
        PredictionFactory(
            type="label",
            barcode="3302740030949",
            data={
                "model": "nutriscore",
                "confidence": 0.816114128,
                "bounding_box": [0.591395915, 0.477426708, 0.688566923, 0.624632716],
            },
            value_tag="en:nutriscore-a",
            value="",
            automatic_processing="f",
        ),
        PredictionFactory(
            type="label",
            barcode="3302740030949",
            data={
                "model": "nutriscore",
                "confidence": 0.913557172,
                "bounding_box": [0.596912444, 0.429353863, 0.70557, 0.592592061],
            },
            value_tag="en:nutriscore-c",
            value="",
            automatic_processing="t",
        ),
        PredictionFactory(
            type="label",
            barcode="3302740030949",
            data={
                "model": "nutriscore",
                "confidence": 0.99035,
                "bounding_box": [0.575399518, 0.472130537, 0.691237211, 0.625134587],
            },
            value_tag="en:nutriscore-e",
            value="",
            automatic_processing="t",
        ),
    ]

    product_insight1 = ProductInsightFactory(
        barcode="3302740030949",
        value_tag="en:nutriscore-c",
        type="label",
        data={
            "model": "nutriscore",
            "confidence": 0.816114128,
            "bounding_box": [0.591395915, 0.477426708, 0.688566923, 0.624632716],
        },
    )

    product_insight2 = ProductInsightFactory(
        barcode="3302740030941",
        value_tag="en:nutriscore-a",
        type="label",
        data={
            "model": "nutriscore",
            "confidence": 0.816114128,
            "bounding_box": [0.591395915, 0.477426708, 0.688566923, 0.624632716],
        },
    )

    product_insight3 = ProductInsightFactory(
        barcode="3302740030942",
        value_tag="en:salmons",
        type="label",
        data={
            "model": "neural",
            "confidence": 0.816114128,
            "bounding_box": [0.591395915, 0.477426708, 0.688566923, 0.624632716],
        },
    )

    product_insight3 = ProductInsightFactory(
        barcode="3302740030943",
        value_tag="en:nutriscore-c",
        type="category",
        data={
            "model": "nutriscore",
            "confidence": 0.816114128,
            "bounding_box": [0.591395915, 0.477426708, 0.688566923, 0.624632716],
        },
    )

    barcode = product_insight1.barcode

    product = {
        "code": barcode,
        "product": {
            "labels": "Sans colorants, Nutriscore, Nutriscore C, Fumé au bois de hêtre",
            "product_name": "Pommes de terre gratinées aux lardons et champignons",
        },
        "status": 1,
        "status_verbose": "product found",
    }

    get_product_storeactual_predictions_all = [
        item.to_dict() for item in predictions_all
    ]

    product_store_mock = mocker.patch(
        "robotoff.insights.importer.get_product_store",
        return_value=fake_product_store(),
    )

    product_mock = mocker.patch(
        "robotoff.insights.annotate.get_product", return_value=product
    )

    actual_product_store_data = [item.to_dict() for item in product_store_mock]

    actual_product_data = [item.to_dict() for item in product_mock]
