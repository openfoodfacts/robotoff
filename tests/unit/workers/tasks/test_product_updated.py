from robotoff.types import (
    InsightImportResult,
    Prediction,
    PredictionType,
    ProductIdentifier,
    ServerType,
)
from robotoff.workers.tasks.product_updated import add_category_insight

# TODO: refactor function under test to make it easier to test
# without extensive mocking and monkey-patching.


def test_add_category_insight_no_insights(mocker):
    mocker.patch(
        "robotoff.workers.tasks.product_updated.predict_category_matcher",
        return_value=[],
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.CategoryClassifier.predict",
        return_value=([], {}),
    )
    import_insights_mock = mocker.patch(
        "robotoff.workers.tasks.product_updated.import_insights"
    )
    imported = add_category_insight("123", {"code": "123"})

    assert not import_insights_mock.called
    assert not imported


def test_add_category_insight_with_ml_insights(mocker):
    barcode = "123"
    product_id = ProductIdentifier(barcode, ServerType.off)
    expected_prediction = Prediction(
        barcode=product_id.barcode,
        type=PredictionType.category,
        value_tag="en:chicken",
        data={"lang": "xx"},
        automatic_processing=True,
        predictor="neural",
        confidence=0.9,
        server_type=product_id.server_type,
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.predict_category_matcher",
        return_value=[],
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.CategoryClassifier.predict",
        return_value=([expected_prediction], {}),
    )
    import_insights_mock = mocker.patch(
        "robotoff.workers.tasks.product_updated.import_insights",
        return_value=InsightImportResult(),
    )
    add_category_insight(product_id, {"code": "123"})

    import_insights_mock.assert_called_once_with(
        [
            Prediction(
                barcode=product_id.barcode,
                type=PredictionType.category,
                value_tag="en:chicken",
                data={"lang": "xx"},
                automatic_processing=True,
                predictor="neural",
                confidence=0.9,
                server_type=product_id.server_type,
            ),
        ],
        ServerType.off,
    )
