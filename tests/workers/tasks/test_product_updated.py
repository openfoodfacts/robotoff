from robotoff import settings
from robotoff.prediction.category.neural.category_classifier import CategoryPrediction
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions
from robotoff.workers.tasks.product_updated import add_category_insight

# TODO: refactor function under test to make it easier to test
# without extensive mocking and monkey-patching.


def test_add_category_insight_no_ml_insights(mocker):
    mocker.patch(
        "robotoff.workers.tasks.product_updated.predict_category_from_product_es",
        return_value=None,
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.CategoryClassifier.predict",
        return_value=None,
    )
    mocker.patch("robotoff.workers.tasks.product_updated.get_product_store")
    import_insights_mock = mocker.patch(
        "robotoff.insights.importer.InsightImporter.import_insights", return_value=1,
    )
    imported = add_category_insight(
        "123", {"code": "123"}, settings.BaseURLProvider().get()
    )

    assert not import_insights_mock.called
    assert not imported


def test_add_category_insight_with_ml_insights(mocker):
    mocker.patch(
        "robotoff.workers.tasks.product_updated.predict_category_from_product_es",
        return_value=None,
    )
    mocker.patch(
        "robotoff.workers.tasks.product_updated.CategoryClassifier.predict",
        return_value=[CategoryPrediction("en:chicken", 0.9)],
    )
    mocker.patch("robotoff.workers.tasks.product_updated.get_product_store")
    import_insights_mock = mocker.patch(
        "robotoff.insights.importer.InsightImporter.import_insights", return_value=1,
    )
    server_domain = settings.BaseURLProvider().get()
    imported = add_category_insight("123", {"code": "123"}, server_domain)

    import_insights_mock.assert_called_once_with(
        [
            ProductPredictions(
                barcode="123",
                type=PredictionType.category,
                predictions=[
                    Prediction(
                        type=PredictionType.category,
                        value_tag="en:chicken",
                        data={"lang": "xx", "model": "neural", "confidence": 0.9},
                    )
                ],
            ),
        ],
        server_domain=server_domain,
        automatic=False,
    )
    assert imported
