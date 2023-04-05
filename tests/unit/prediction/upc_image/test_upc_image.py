import cv2
import pytest

from robotoff import settings
from robotoff.prediction.upc_image import UPCImageType, find_image_is_upc

data_dir = settings.TEST_DATA_DIR / "upc_image"


@pytest.mark.parametrize(
    "imgpath, expected",
    [
        (data_dir / "upc1.jpg", UPCImageType.UPC_IMAGE),
        (data_dir / "upc2.jpg", UPCImageType.UPC_IMAGE),
        (data_dir / "upc3.jpg", UPCImageType.UPC_IMAGE),
        (data_dir / "small_upc1.jpg", UPCImageType.SMALL_UPC),
        (data_dir / "small_upc2.jpg", UPCImageType.SMALL_UPC),
        (data_dir / "small_upc3.jpg", UPCImageType.SMALL_UPC),
        (data_dir / "no_upc1.jpg", UPCImageType.NO_UPC),
        (data_dir / "no_upc2.jpg", UPCImageType.NO_UPC),
        (data_dir / "no_upc3.jpg", UPCImageType.NO_UPC),
    ],
)
def test_find_image_is_upc(imgpath, expected):
    image = cv2.imread(str(imgpath))

    assert find_image_is_upc(image)[1] == expected
