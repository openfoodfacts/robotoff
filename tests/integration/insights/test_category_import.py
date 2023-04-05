import pytest

from robotoff import settings
from robotoff.insights.importer import import_insights
from robotoff.models import ProductInsight
from robotoff.products import Product
from robotoff.types import Prediction, PredictionType

from ..models_utils import PredictionFactory, ProductInsightFactory, clean_db

insight_id1 = "94371643-c2bc-4291-a585-af2cb1a5270a"
barcode1 = "00001"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        # clean db
        clean_db()
        # a category already exists
        PredictionFactory(
            barcode=barcode1,
            type="category",
            value_tag="en:salmons",
            automatic_processing=False,
            predictor="matcher",
        )
        ProductInsightFactory(
            id=insight_id1,
            barcode=barcode1,
            type="category",
            value_tag="en:salmons",
            predictor="matcher",
        )
        # Run the test case.
        yield
        # Tear down.
        clean_db()


def matcher_prediction(category):
    return Prediction(
        barcode=barcode1,
        type=PredictionType.category,
        value_tag=category,
        data={
            "lang": "en",
            "product_name": "test",
        },
        automatic_processing=False,
        predictor="matcher",
    )


def neural_prediction(category, confidence=0.7, auto=False):
    return Prediction(
        barcode=barcode1,
        type=PredictionType.category,
        value_tag=category,
        data={"lang": "xx"},
        automatic_processing=auto,
        predictor="neural",
        confidence=confidence,
    )


class TestCategoryImporter:
    """Test category importer

    We only test the scenarios that are of actual use
    """

    def fake_product_store(self):
        return {barcode1: Product({"categories_tags": ["en:fish"]})}

    def _run_import(self, predictions, product_store=None):
        if product_store is None:
            product_store = self.fake_product_store()
        return import_insights(
            predictions,
            server_domain=settings.BaseURLProvider.server_domain(),
            product_store=product_store,
        )

    @pytest.mark.parametrize(
        "predictions",
        [
            # category already on product
            [matcher_prediction("en:fish")],
            [neural_prediction("en:fish")],
            # category already in insights
            [matcher_prediction("en:salmons")],
            [neural_prediction("en:salmons")],
            # both
            [
                matcher_prediction("en:fish"),
                matcher_prediction("en:salmons"),
                neural_prediction("en:fish"),
                neural_prediction("en:salmons"),
            ],
        ],
    )
    def test_import_one_same_value_tag(self, predictions):
        """Test when there is a single import, but the value_tag stays the
        same."""
        original_insights = ProductInsight.select()
        assert len(original_insights) == 1
        original_timestamp = original_insights[0].timestamp
        import_result = self._run_import(predictions)
        assert import_result.created_insights_count() == 0
        assert import_result.updated_insights_count() == 1
        assert import_result.deleted_insights_count() == 0
        # no insight created
        insights = list(ProductInsight.select())
        assert len(insights) == 1
        insight = insights[0]
        assert insight.value_tag == "en:salmons"
        assert insight.timestamp > original_timestamp

    @pytest.mark.parametrize(
        "predictions",
        [
            # new category ES
            [matcher_prediction("en:smoked-salmons")],
            # new category Neural
            [neural_prediction("en:smoked-salmons")],
            # both, same category
            [
                matcher_prediction("en:smoked-salmons"),
                neural_prediction("en:smoked-salmons"),
            ],
        ],
    )
    def test_import_one_different_value_tag(self, predictions):
        """Test when a more precise category is available as prediction: the
        prediction should be used as insight instead of the less precise one."""
        import_result = self._run_import(predictions)
        assert import_result.created_insights_count() == 1
        assert import_result.updated_insights_count() == 0
        assert import_result.deleted_insights_count() == 1
        # no insight created
        assert ProductInsight.select().count() == 1
        inserted = ProductInsight.get(ProductInsight.id != insight_id1)
        assert inserted.value_tag == "en:smoked-salmons"
        assert inserted.server_domain == settings.BaseURLProvider.server_domain()
        assert not inserted.automatic_processing

    def test_import_auto(self):
        import_result = self._run_import(
            [neural_prediction("en:smoked-salmons", confidence=0.91, auto=True)]
        )
        assert import_result.created_insights_count() == 1
        assert import_result.updated_insights_count() == 0
        assert import_result.deleted_insights_count() == 1
        # no insight created
        assert ProductInsight.select().count() == 1
        inserted = ProductInsight.get(ProductInsight.id != insight_id1)
        assert inserted.value_tag == "en:smoked-salmons"
        assert inserted.server_domain == settings.BaseURLProvider.server_domain()
        assert inserted.automatic_processing

    @pytest.mark.parametrize(
        "predictions",
        [
            # new category ES
            [matcher_prediction("en:smoked-salmons")],
            # new category Neural
            [neural_prediction("en:smoked-salmons", confidence=0.99, auto=True)],
        ],
    )
    def test_import_product_not_in_store(self, predictions):
        # we should not create insight for non existing products !
        import_result = self._run_import(predictions, product_store={barcode1: None})
        assert import_result.created_insights_count() == 0
        assert import_result.updated_insights_count() == 0
        assert import_result.deleted_insights_count() == 0
        # no insight created
        assert ProductInsight.select().count() == 1
