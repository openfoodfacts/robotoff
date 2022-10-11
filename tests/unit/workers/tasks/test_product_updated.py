from robotoff import settings
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.workers.tasks.product_updated import add_category_insight

# TODO: refactor function under test to make it easier to test
# without extensive mocking and monkey-patching.


def test_add_category_insight_no_insights(mocker):
    mocker.patch(
        "robotoff.workers.tasks.product_updated.predict_category_from_product_es",
        return_value=None,
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.CategoryClassifier.predict",
        return_value=[],
    )
    import_insights_mock = mocker.patch(
        "robotoff.workers.tasks.product_updated.import_insights"
    )
    imported = add_category_insight(
        "123", {"code": "123"}, settings.BaseURLProvider().get()
    )

    assert not import_insights_mock.called
    assert not imported


def test_add_category_insight_with_ml_insights(mocker):
    expected_prediction = Prediction(
        barcode="123",
        type=PredictionType.category,
        value_tag="en:chicken",
        data={"lang": "xx", "model": "neural", "confidence": 0.9},
        automatic_processing=True,
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.predict_category_from_product_es",
        return_value=None,
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.CategoryClassifier.predict",
        return_value=[expected_prediction],
    )
    import_insights_mock = mocker.patch(
        "robotoff.workers.tasks.product_updated.import_insights",
        return_value=1,
    )
    server_domain = settings.BaseURLProvider().get()
    imported = add_category_insight("123", {"code": "123"}, server_domain)

    import_insights_mock.assert_called_once_with(
        [
            Prediction(
                barcode="123",
                type=PredictionType.category,
                value_tag="en:chicken",
                data={"lang": "xx", "model": "neural", "confidence": 0.9},
                automatic_processing=True,
            )
        ],
        server_domain,
        automatic=True,
    )

    assert imported
