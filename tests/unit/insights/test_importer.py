import uuid
from typing import Any, Dict, List, Optional

from robotoff.insights.importer import ProductWeightImporter
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions

DEFAULT_BARCODE = "3760094310634"
DEFAULT_SERVER_DOMAIN = "api.openfoodfacts.org"


class FakeProductStore:
    def __init__(self, data: Optional[Dict] = None):
        self.data = data or {}

    def is_real_time(self):
        return False

    def __getitem__(self, item):
        return self.data.get(item)


class TestProductWeightImporter:
    @staticmethod
    def generate_prediction(value, data: Dict[str, Any]):
        return Prediction(
            type=PredictionType.product_weight,
            data=data,
            automatic_processing=None,
            predictor="ocr",
        )

    @staticmethod
    def get_product_weight_predictions(
        predictions: List[Prediction],
        barcode: Optional[str] = None,
        source_image: Optional[str] = None,
    ):
        return ProductPredictions(
            predictions=predictions,
            barcode=barcode or DEFAULT_BARCODE,
            type=PredictionType.product_weight,
            source_image=source_image,
        )

    def test_generate_insight_single(self, mocker):
        mocker.patch(
            "robotoff.insights.importer.ProductWeightImporter.get_seen_count",
            return_value=0,
        )
        product_store = FakeProductStore()
        importer = ProductWeightImporter(product_store)
        value = "poids net: 30 g"
        insight_data = {"matcher_type": "with_mention", "value": value}
        predictions = self.get_product_weight_predictions(
            [self.generate_prediction(value, insight_data)], DEFAULT_BARCODE
        )
        insights = list(
            importer.generate_insights(
                [predictions], automatic=True, server_domain=DEFAULT_SERVER_DOMAIN
            )
        )
        assert len(insights) == 1
        insight = insights[0]
        assert insight.automatic_processing is True
        assert insight.barcode == DEFAULT_BARCODE
        assert insight.type == "product_weight"
        assert insight.data == insight_data
        assert insight.value_tag is None
        assert insight.reserved_barcode is False
        assert insight.server_domain == DEFAULT_SERVER_DOMAIN
        assert insight.server_type == "off"
        # check that id is a valid UUID
        uuid.UUID(insight.id)
