import pytest
from robotoff.insights.ocr import PRODUCT_WEIGHT_REGEX, OCRRegex, BRAND_REGEX, \
    BoundingPoly, ImageOrientation


@pytest.mark.parametrize('input_str,is_match', [
    ("poids net à l'emballage: 500g", True),
    ("poids 2kg", True),
    ("poids 2kgv", False),
    ("net wt. 1.4 fl oz", True),
    ("other string", False),
    ("1.4 g", False),
    ("2 l", False),
])
def test_product_weight_with_mention_regex(input_str: str, is_match: bool):
    with_mention_ocr_regex: OCRRegex = PRODUCT_WEIGHT_REGEX['with_mention']
    with_mention_regex = with_mention_ocr_regex.regex

    assert (with_mention_regex.match(input_str) is not None) == is_match


@pytest.mark.parametrize('input_str,is_match', [
    ("other string", False),
    ("carre", False),
    ("carrefour", True),
    ("monoprix p'tit prix", True),
    ("marks & spencer", True),
    ("nestlé", True),
    ("nestle", True),
    ("carrefour gaby", True),
    ("carrefour baby", True),
    ("dr. oetker", True),
    ("dr oetker", True),
    ("m-budget", True),
    ("la belle iloise", True),
    ("la belle-îloise", True),
])
def test_brand_regex(input_str: str, is_match: bool):
    regex = BRAND_REGEX.regex
    assert (regex.match(input_str) is not None) == is_match


def generate_bounding_poly(*items):
    vertices = [{'x': item[0], 'y': item[1]}
                for item in items]
    data = {
        'vertices': vertices
    }
    return BoundingPoly(data)


class TestBoundingPoly:
    @pytest.mark.parametrize('bounding_poly,orientation', [
        (generate_bounding_poly((66, 458), (60, 348), (94, 346), (100, 456)),
         ImageOrientation.left),
        (generate_bounding_poly((66, 458), (60, 340), (94, 346), (100, 456)),
         ImageOrientation.left),
        (generate_bounding_poly((1106, 414), (1178, 421), (1175, 446),
                                (1103, 439)),
         ImageOrientation.up),
        (generate_bounding_poly((1106, 421), (1178, 414), (1175, 446),
                                (1103, 439)),
         ImageOrientation.up),
    ])
    def test_detect_orientation(self,
                                bounding_poly: BoundingPoly,
                                orientation: ImageOrientation):
        assert bounding_poly.detect_orientation() == orientation
