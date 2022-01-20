import pytest

from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions


def test_product_predictions_merge():
    predictions_1 = [
        Prediction(type=PredictionType.label, data={}, value_tag="en:organic")
    ]
    product_predictions_1 = ProductPredictions(
        predictions=predictions_1,
        barcode="123",
        type=PredictionType.label,
        source_image="/123/1.jpg",
    )

    predictions_2 = [Prediction(type=PredictionType.label, data={}, value_tag="en:pgi")]
    product_predictions_2 = ProductPredictions(
        predictions=predictions_2,
        barcode="123",
        type=PredictionType.label,
        source_image="/123/1.jpg",
    )

    merged_product_predictions = ProductPredictions.merge(
        [product_predictions_1, product_predictions_2]
    )

    assert merged_product_predictions.type == PredictionType.label
    assert merged_product_predictions.barcode == "123"
    assert merged_product_predictions.source_image == "/123/1.jpg"
    assert merged_product_predictions.predictions == predictions_1 + predictions_2


def test_product_predictions_failed_merge():
    with pytest.raises(ValueError):
        ProductPredictions.merge([])

    with pytest.raises(ValueError):
        ProductPredictions.merge(
            [
                ProductPredictions(
                    predictions=[],
                    barcode="123",
                    type=PredictionType.label,
                    source_image="/123/1.jpg",
                ),
                ProductPredictions(
                    predictions=[],
                    barcode="234",
                    type=PredictionType.label,
                    source_image="/123/1.jpg",
                ),
            ]
        )

    with pytest.raises(ValueError):
        ProductPredictions.merge(
            [
                ProductPredictions(
                    predictions=[],
                    barcode="123",
                    type=PredictionType.label,
                    source_image="/123/1.jpg",
                ),
                ProductPredictions(
                    predictions=[],
                    barcode="123",
                    type=PredictionType.category,
                    source_image="/123/1.jpg",
                ),
            ]
        )

    with pytest.raises(ValueError):
        ProductPredictions.merge(
            [
                ProductPredictions(
                    predictions=[],
                    barcode="123",
                    type=PredictionType.label,
                    source_image="/123/1.jpg",
                ),
                ProductPredictions(
                    predictions=[],
                    barcode="123",
                    type=PredictionType.label,
                    source_image="/123/2.jpg",
                ),
            ]
        )

    with pytest.raises(ValueError):
        ProductPredictions.merge(
            [
                ProductPredictions(
                    predictions=[],
                    barcode="123",
                    type=PredictionType.label,
                    source_image="/123/1.jpg",
                ),
                ProductPredictions(
                    predictions=[],
                    barcode="123",
                    type=PredictionType.category,
                    source_image="/123/2.jpg",
                ),
            ]
        )
