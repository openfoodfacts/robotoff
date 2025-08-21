# import cv2
# import numpy as np
# import pytest
# from openfoodfacts.images import download_image

# from robotoff import settings
# from robotoff.prediction.upc_image import UPCImageType, find_image_is_upc

# Run UPC detection to detect if the image is dominated by a UPC (and thus
# should not be a product selected image)
# UPC detection is buggy since the upgrade to OpenCV 4.10
# The test is disabled until the issue is resolved


# @pytest.mark.parametrize(
#     "image_url, expected",
#     [
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/upc1.jpg",
#             UPCImageType.UPC_IMAGE,
#         ),
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/upc2.jpg",
#             UPCImageType.UPC_IMAGE,
#         ),
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/upc3.jpg",
#             UPCImageType.UPC_IMAGE,
#         ),
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/small_upc1.jpg",
#             UPCImageType.SMALL_UPC,
#         ),
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/small_upc2.jpg",
#             UPCImageType.SMALL_UPC,
#         ),
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/small_upc3.jpg",
#             UPCImageType.SMALL_UPC,
#         ),
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/no_upc1.jpg",
#             UPCImageType.NO_UPC,
#         ),
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/no_upc2.jpg",
#             UPCImageType.NO_UPC,
#         ),
#         (
#             "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/no_upc3.jpg",
#             UPCImageType.NO_UPC,
#         ),
#     ],
# )
# def test_find_image_is_upc(image_url: str, expected: UPCImageType):
#     response = download_image(image_url, return_struct=True)
#     arr = np.frombuffer(response.image_bytes, dtype=np.uint8)
#     image = cv2.imdecode(arr, cv2.IMREAD_COLOR)

#     assert find_image_is_upc(image)[1] == expected
