from PIL import Image
from tests import data
from robotoff.insights.extraction import get_predictions_from_image
from robotoff.insights.importer import import_insights
from unittest.mock import Mock


def test_import_insights_from_image(mock):
    barcode = "3302740030949"
    source_image = '/330/274/003/0949/6.jpg '
    ocr_url = 'https://world.openfoodfacts.org/images/products/802/509/314/0251/4.json'
    server_domain = 'api.openfoodfacts.org'

    expected_predictions_all =  [
        PredictionFactory(type='label',  barcode=3302740030949, data={"model": "nutriscore", "confidence": 0.871872, "bounding_box": [1441.3848, 1036.8024, 1685.6928, 1430.2488]}, value_tag="en:nutriscore-c", value="", automatic_processing=False),
        PredictionFactory(type='label',  barcode=3302740030949, data={"model": "nutriscore", "confidence": 0.816114128,  "bounding_box": [0.591395915, 0.477426708, 0.688566923, 0.624632716]}, value_tag="en:nutriscore-a", value="", automatic_processing=False),
        PredictionFactory(type='label',  barcode=3302740030949, data={"model": "nutriscore", "confidence": 0.913557172, "bounding_box": [0.596912444, 0.429353863, 0.70557, 0.592592061]}, value_tag="en:nutriscore-c", value="", automatic_processing=False),
        PredictionFactory(type='label',  barcode=3302740030949, data={"model": "nutriscore", "confidence": 0.99035, "bounding_box": [0.575399518, 0.472130537, 0.691237211, 0.625134587]}, value_tag="en:nutriscore-e", value="", automatic_processing=False)
    ]

    get_predictions_from_image = mock.Mock(return_value=expected_predictions_all)

    get_product = {"code":"3302740030949","product":{"labels":"Sans colorants, Nutriscore, Nutriscore C, Fumé au bois de hêtre","product_name":"Pommes de terre gratinées aux lardons et champignons"},"status":1,"status_verbose":"product found"}

    # import_insights = mock.Mock(return_value=)
    

