import pytest

from robotoff import settings
from robotoff.insights.dataclass import InsightType
from robotoff.insights.importer import InsightImporterFactory
from robotoff.models import ProductInsight
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions
from robotoff.products import Product

insight_id1 = "94371643-c2bc-4291-a585-af2cb1a5270a"
barcode1 = "00001"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    ProductInsight.delete().execute()
    # a category already exists
    ProductInsight.create(
        id=insight_id1,
        data="{}",
        barcode=barcode1,
        type="category",
        n_votes=0,
        latent=False,
        value_tag="en:Salmons",
        server_domain=settings.OFF_SERVER_DOMAIN,
        automatic_processing=False,
        unique_scans_n=0,
        reserved_barcode=False,
    )
    # Run the test case.
    yield
    # Tear down.
    ProductInsight.delete().execute()


def matcher_prediction(category):
    return Prediction(
        type=PredictionType.category,
        value_tag=category,
        data={
            "lang": "en",
            "product_name": "test",
            "model": "matcher",
        },
    )


def neural_prediction(category, confidence=0.7, auto=False):
    return Prediction(
        type=PredictionType.category,
        value_tag=category,
        data={"lang": "xx", "model": "neural", "confidence": confidence},
        automatic_processing=auto,
    )


class TestCategoryImporter:
    """Test category importer

    We only test the scenarios that are of actual use
    """

    def fake_product_store(self):
        return {barcode1: Product({"categories_tags": ["en:Fish"]})}

    def _run_import(self, predictions):
        insights = [
            ProductPredictions(
                barcode=barcode1,
                type=PredictionType.category,
                predictions=predictions,
            )
        ]
        importer = InsightImporterFactory.create(
            InsightType.category, self.fake_product_store()
        )
        imported = importer.import_insights(
            insights,
            server_domain=settings.OFF_SERVER_DOMAIN,
            automatic=True,
        )
        return imported

    @pytest.mark.parametrize(
        "predictions",
        [
            # empty list
            [],
            # category already on product
            [matcher_prediction("en:Fish")],
            [neural_prediction("en:Fish")],
            # category already in insights
            [matcher_prediction("en:Salmons")],
            [neural_prediction("en:Salmons")],
            # both
            [
                matcher_prediction("en:Fish"),
                matcher_prediction("en:Salmons"),
                neural_prediction("en:Fish"),
                neural_prediction("en:Salmons"),
            ],
        ],
    )
    def test_import_nothing(self, predictions):
        imported = self._run_import(predictions)
        assert imported == 0
        # no insight created
        assert ProductInsight.select().count() == 1

    @pytest.mark.parametrize(
        "predictions",
        [
            # new category ES
            [matcher_prediction("en:Smoked Salmons")],
            # new category Neural
            [neural_prediction("en:Smoked Salmons")],
            # both, same category
            [
                matcher_prediction("en:Smoked Salmons"),
                neural_prediction("en:Smoked Salmons"),
            ],
        ],
    )
    def test_import_one(self, predictions):
        imported = self._run_import(predictions)
        assert imported == 1
        # no insight created
        assert ProductInsight.select().count() == 2
        inserted = ProductInsight.get(ProductInsight.id != insight_id1)
        assert inserted.value_tag == "en:Smoked Salmons"
        assert inserted.server_domain == settings.OFF_SERVER_DOMAIN
        assert not inserted.latent
        assert not inserted.automatic_processing

    def test_import_auto(self):
        imported = self._run_import(
            [neural_prediction("en:Smoked Salmons", confidence=0.91, auto=True)]
        )
        assert imported == 1
        # no insight created
        assert ProductInsight.select().count() == 2
        inserted = ProductInsight.get(ProductInsight.id != insight_id1)
        assert inserted.value_tag == "en:Smoked Salmons"
        assert inserted.server_domain == settings.OFF_SERVER_DOMAIN
        assert not inserted.latent
        assert inserted.automatic_processing
