from typing import Optional

import pytest

from robotoff.off import get_barcode_from_url


@pytest.mark.parametrize(
    "url,output",
    [
        (
            "https://world.openfoodfacts.org/images/products/541/012/672/6954/1.jpg",
            "5410126726954",
        ),
        (
            "https://world.openfoodfacts.org/images/products/541/012/672/6954/1.json",
            "5410126726954",
        ),
        ("https://world.openfoodfacts.org/images/products/invalid/1.json", None),
        ("https://world.openfoodfacts.org/images/products/252/535.bk/1.jpg", None),
    ],
)
def test_get_barcode_from_url(url: str, output: Optional[str]):
    assert get_barcode_from_url(url) == output
