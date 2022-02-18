import datetime

import pytest

from robotoff import settings
from robotoff.insights.importer import import_insights
from robotoff.models import Prediction as PredictionModel
from robotoff.models import ProductInsight
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.products import Product

insight_id1 = "94371643-c2bc-4291-a585-af2cb1a5270a"
barcode1 = "00001"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    ProductInsight.delete().execute()
    PredictionModel.delete().execute()
    # a category already exists
    PredictionModel.create(
        data={},
        barcode=barcode1,
        type="category",
        value_tag="en:salmons",
        server_domain=settings.OFF_SERVER_DOMAIN,
        automatic_processing=False,
        timestamp=datetime.datetime.utcnow(),
    )
    ProductInsight.create(
        id=insight_id1,
        data={},
        barcode=barcode1,
        type="category",
        value_tag="en:salmons",
        server_domain=settings.OFF_SERVER_DOMAIN,
        automatic_processing=False,
        unique_scans_n=0,
        n_votes=0,
        reserved_barcode=False,
        timestamp=datetime.datetime.utcnow(),
    )
    # Run the test case.
    yield
    # Tear down.
    ProductInsight.delete().execute()
    PredictionModel.delete().execute()


def matcher_prediction(category):
    return Prediction(
        barcode=barcode1,
        type=PredictionType.category,
        value_tag=category,
        data={
            "lang": "en",
            "product_name": "test",
            "model": "matcher",
        },
        automatic_processing=False,
    )


def neural_prediction(category, confidence=0.7, auto=False):
    return Prediction(
        barcode=barcode1,
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

    def _run_import(self, predictions, product_store=None):
        if product_store is None:
            product_store = self.fake_product_store()
        imported = import_insights(
            predictions,
            server_domain=settings.OFF_SERVER_DOMAIN,
            automatic=True,
            product_store=product_store,
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
            [matcher_prediction("en:salmons")],
            [neural_prediction("en:salmons")],
            # both
            [
                matcher_prediction("en:Fish"),
                matcher_prediction("en:salmons"),
                neural_prediction("en:Fish"),
                neural_prediction("en:salmons"),
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
    def test_import_one(self, predictions):
        imported = self._run_import(predictions)
        assert imported == 1
        # no insight created
        assert ProductInsight.select().count() == 1
        inserted = ProductInsight.get(ProductInsight.id != insight_id1)
        assert inserted.value_tag == "en:smoked-salmons"
        assert inserted.server_domain == settings.OFF_SERVER_DOMAIN
        assert not inserted.automatic_processing

    def test_import_auto(self):
        imported = self._run_import(
            [neural_prediction("en:smoked-salmons", confidence=0.91, auto=True)]
        )
        assert imported == 1
        # no insight created
        assert ProductInsight.select().count() == 1
        inserted = ProductInsight.get(ProductInsight.id != insight_id1)
        assert inserted.value_tag == "en:smoked-salmons"
        assert inserted.server_domain == settings.OFF_SERVER_DOMAIN
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
        imported = self._run_import(predictions, product_store={barcode1: None})
        assert imported == 0
        # no insight created
        assert ProductInsight.select().count() == 1
