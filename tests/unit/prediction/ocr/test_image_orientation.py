import pytest

from robotoff.prediction.ocr.dataclass import BoundingPoly, ImageOrientation


def generate_bounding_poly(*items):
    vertices = [{"x": item[0], "y": item[1]} for item in items]
    data = {"vertices": vertices}
    return BoundingPoly(data)


class TestBoundingPoly:
    @pytest.mark.parametrize(
        "bounding_poly,orientation",
        [
            (
                generate_bounding_poly((66, 458), (60, 348), (94, 346), (100, 456)),
                ImageOrientation.left,
            ),
            (
                generate_bounding_poly((66, 458), (60, 340), (94, 346), (100, 456)),
                ImageOrientation.left,
            ),
            (
                generate_bounding_poly(
                    (1106, 414), (1178, 421), (1175, 446), (1103, 439)
                ),
                ImageOrientation.up,
            ),
            (
                generate_bounding_poly(
                    (1106, 421), (1178, 414), (1175, 446), (1103, 439)
                ),
                ImageOrientation.up,
            ),
        ],
    )
    def test_detect_orientation(
        self, bounding_poly: BoundingPoly, orientation: ImageOrientation
    ):
        assert bounding_poly.detect_orientation() == orientation
