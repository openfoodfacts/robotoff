import requests
from PIL import Image

from robotoff import settings
from tests.integration.models_utils import PredictionFactory


def test_import_insights_from_image(mocker):
    barcode = "3302740030949"
    source_image = "https://world.openfoodfacts.org/images/products/330/274/003/0949/front_fr.110.400.jpg"
    ocr_url = "https://world.openfoodfacts.org/images/products/802/509/314/0251/4.json"
    server_domain = settings.OFF_SERVER_DOMAIN

    image = Image.open(requests.get(source_image, stream=True).raw)

    mock_import_insights = mocker.patch(
        "robotoff.insights.importer.import_insights", return_value=4
    )
    mock_get_predictions_from_image = mocker.patch(
        "robotoff.insights.extraction.get_predictions_from_image"
    )

    predictions_list = [
        PredictionFactory(
            type="label",
            barcode=3302740030949,
            data={
                "model": "nutriscore",
                "confidence": 0.871872,
                "bounding_box": [1441.3848, 1036.8024, 1685.6928, 1430.2488],
            },
            value_tag="en:nutriscore-c",
            value="",
            automatic_processing=False,
        ),
        PredictionFactory(
            type="label",
            barcode=3302740030949,
            data={
                "model": "nutriscore",
                "confidence": 0.816114128,
                "bounding_box": [0.591395915, 0.477426708, 0.688566923, 0.624632716],
            },
            value_tag="en:nutriscore-a",
            value="",
            automatic_processing=False,
        ),
        PredictionFactory(
            type="label",
            barcode=3302740030949,
            data={
                "model": "nutriscore",
                "confidence": 0.913557172,
                "bounding_box": [0.596912444, 0.429353863, 0.70557, 0.592592061],
            },
            value_tag="en:nutriscore-c",
            value="",
            automatic_processing=False,
        ),
        PredictionFactory(
            type="label",
            barcode=3302740030949,
            data={
                "model": "nutriscore",
                "confidence": 0.99035,
                "bounding_box": [0.575399518, 0.472130537, 0.691237211, 0.625134587],
            },
            value_tag="en:nutriscore-e",
            value="",
            automatic_processing=False,
        ),
    ]

    mock_import_insights.assert_called_once_with(
        predictions=predictions_list,
        server_domain=server_domain,
        automatic=True,
    )

    mock_get_predictions_from_image.assert_called_once_with(
        barcode=barcode, image=image, source_image=source_image, ocr_url=ocr_url
    )
