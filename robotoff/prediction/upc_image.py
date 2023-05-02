from enum import Enum
from typing import Optional

import cv2
import numpy as np

from robotoff.utils import get_logger

logger = get_logger(__name__)


class UPCImageType(Enum):
    """This enum is used to determine the type of image regarding UPC
    information."""

    # The image is a UPC Image which means that a UPC has a greater area in the
    # image than the threshold and thus it is a poor selected photo
    UPC_IMAGE = "UPC_IMAGE"

    # The image is not a UPC Image but a UPC is present in the image, however
    # it is too small to be considered a UPC Image
    SMALL_UPC = "SMALL_UPC"

    # The image is not a UPC Image and no UPC is present in the image
    NO_UPC = "NO_UPC"


def get_polygon_area(box: np.ndarray) -> float:
    """This method determines the area of a polygon given a list of points
    The formula for determining area of the points is the shoelace formula
    https://en.wikipedia.org/wiki/Shoelace_formula

    For additional info look at
    https://stackoverflow.com/questions/24467972/calculate-area-of-polygon-given-x-y-coordinates

    :param box: list of points in format [[y, x], ...] (opencvformat)
    :return: float of the area of the polygon that is our bounding box
    """
    x = np.array([pt[1] for pt in box])
    y = np.array([pt[0] for pt in box])
    x, y
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def get_is_upc_image_from_image(
    image: np.ndarray,
) -> tuple[float, UPCImageType, Optional[list[list[float]]]]:
    """This method determines if an image is a UPC_Image or not.

    A UPC_Image is defined as an image that has a UPC (=barcode) with a high
    percentage area in the image and thus it is a poor selected photo.

    :param image: numpy array of the image
    :return: tuple containing the percentage area of the image taken by the
        UPC, the UPCImageType and the polygon with absolute coordinates
        of the UPC (or None if no UPC was detected)
    """
    AREA_THRESHOLD = 0.09  # Best result thus far in testing, a UPC with a
    # greater area in the image means it is a "UPC_Image"

    # use built in barcode model from opencvcontrib
    bd = cv2.barcode.BarcodeDetector()

    # returns a tuple of the barcode data ending in the points of the bounding
    # box other return values in order are a bool of whether the barcode was
    # detected, any strings found in the region as a tuple, and the type of
    # barcode (EAN_13, etc)
    _, _, _, polygon = bd.detectAndDecode(image)

    if polygon is not None:
        # means we have detected a UPC
        polygon = polygon.astype(int)[0]
        area = get_polygon_area(polygon)
        y, x, _ = image.shape
        image_total_area = x * y

        barcode_area = area / image_total_area
        if barcode_area > AREA_THRESHOLD:
            return barcode_area, UPCImageType.UPC_IMAGE, polygon.tolist()
        else:
            # if this point is reached then the UPC is present but too small
            # for a UPC_Image label
            return barcode_area, UPCImageType.SMALL_UPC, polygon.tolist()

    return 0, UPCImageType.NO_UPC, None  # not a UPC_Image


def find_image_is_upc(
    image: np.ndarray,
) -> tuple[float, UPCImageType, Optional[list[list[float]]]]:
    """This function determines if an image is a UPC_Image or not.
    A UPC_Image is defined as an image that has a UPC (=barcode) with a high
    percentage area in the image and thus it is a poor selected photo.

    :param image: numpy array of the image
    :return: tuple containing the percentage area of the image taken by the
        UPC, the UPCImageType and the polygon with absolute coordinates
        of the UPC (or None if no UPC was detected)
    """
    pct_area, prediction_class, polygon = get_is_upc_image_from_image(image)
    logger.debug(
        "Result is %s (area: %s, polygon: %s)",
        prediction_class,
        pct_area,
        polygon,
    )
    return pct_area, prediction_class, polygon
