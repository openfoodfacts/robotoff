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


DEFAULT_BARCODE = "123"
DEFAULT_PRODUCT_ID = ProductIdentifier(DEFAULT_BARCODE, ServerType.off)


def test_add_category_insight_no_insights(mocker):
    mocker.patch(
        "robotoff.workers.tasks.common.CategoryClassifier.predict",
        return_value=([], {}),
    )
    import_insights_mock = mocker.patch("robotoff.workers.tasks.common.import_insights")
    add_category_insight(DEFAULT_PRODUCT_ID, {"code": DEFAULT_BARCODE})

    assert not import_insights_mock.called


def test_add_category_insight_with_ml_insights(mocker):
    expected_prediction = Prediction(
        barcode=DEFAULT_PRODUCT_ID.barcode,
        type=PredictionType.category,
        value_tag="en:chicken",
        data={"lang": "xx"},
        automatic_processing=True,
        predictor="neural",
        confidence=0.9,
        server_type=DEFAULT_PRODUCT_ID.server_type,
    )
    mocker.patch(
        "robotoff.workers.tasks.common.CategoryClassifier.predict",
        return_value=([expected_prediction], {}),
    )
    import_insights_mock = mocker.patch(
        "robotoff.workers.tasks.common.import_insights",
        return_value=InsightImportResult(),
    )
    add_category_insight(
        DEFAULT_PRODUCT_ID, {"code": DEFAULT_BARCODE, "schema_version": 1003}
    )

    import_insights_mock.assert_called_once_with(
        [
            Prediction(
                barcode=DEFAULT_PRODUCT_ID.barcode,
                type=PredictionType.category,
                value_tag="en:chicken",
                data={"lang": "xx"},
                automatic_processing=True,
                predictor="neural",
                confidence=0.9,
                server_type=DEFAULT_PRODUCT_ID.server_type,
            ),
        ],
        ServerType.off,
    )
