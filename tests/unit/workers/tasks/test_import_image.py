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
    
    expected_predictions_all = get_predictions_from_image(barcode, data.image, source_image, ocr_url)

    get_predictions_from_image = mock.Mock(return_value=data.expected_predictions_all)