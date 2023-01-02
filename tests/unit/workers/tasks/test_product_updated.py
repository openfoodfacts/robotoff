from robotoff import settings
from robotoff.prediction.types import Prediction
from robotoff.types import InsightImportResult, PredictionType
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
        return_value=[],
    )
    import_insights_mock = mocker.patch(
        "robotoff.workers.tasks.product_updated.import_insights"
    )
    imported = add_category_insight(
        "123", {"code": "123"}, settings.BaseURLProvider.world()
    )

    assert not import_insights_mock.called
    assert not imported


def test_add_category_insight_with_ml_insights(mocker):
    expected_prediction = Prediction(
        barcode="123",
        type=PredictionType.category,
        value_tag="en:chicken",
        data={"lang": "xx"},
        automatic_processing=True,
        predictor="neural",
        confidence=0.9,
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.predict_category_matcher",
        return_value=[],
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.CategoryClassifier.predict",
        return_value=[expected_prediction],
    )
    import_insights_mock = mocker.patch(
        "robotoff.workers.tasks.product_updated.import_insights",
        return_value=InsightImportResult(),
    )
    server_domain = settings.BaseURLProvider.world()
    add_category_insight("123", {"code": "123"}, server_domain)

    import_insights_mock.assert_called_once_with(
        [
            Prediction(
                barcode="123",
                type=PredictionType.category,
                value_tag="en:chicken",
                data={"lang": "xx"},
                automatic_processing=True,
                predictor="neural",
                confidence=0.9,
            )
        ],
        server_domain,
    )
