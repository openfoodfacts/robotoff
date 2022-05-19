from PIL import Image
from robotoff.utils import get_image_from_url, get_logger, http_session

image = get_image_from_url('https://world.openfoodfacts.org/images/products/802/509/314/0251/4.jpg', error_raise=False)


def test_import_insights_from_image(mocker):
    barcode = "4640028621441"
    source_image = 'https://world.openfoodfacts.org/images/products/802/509/314/0251/4.jpg'
    ocr_url = 'https://world.openfoodfacts.org/images/products/802/509/314/0251/4.json'
    sever_domain = 'http://openfoodfacts.org/'
    
    expected_predictions_all = get_predictions_from_image(barcode, image, source_image, ocr_url, sever_domain)

    predictions_all_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.import_insights_from_image.get_predictions_from_image",
        return_value=[expected_predictions_all],
    )

    imported_mock = import_insights(predictions_all, server_domain, automatic=True)

    