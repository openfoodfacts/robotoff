from typing import Optional

import pytest

from robotoff.insights.extraction import get_barcode_from_url, get_source_from_ocr_url


@pytest.mark.parametrize(
    "url,output",
    [
        ("/541/012/672/6954/1.jpg", "5410126726954"),
        ("/541/012/672/6954/1.json", "5410126726954"),
        ("/invalid/1.json", None),
        ("/252/535.bk/1.jpg", None),
    ],
)
def test_get_barcode_from_url(url: str, output: Optional[str]):
    assert get_barcode_from_url(url) == output


@pytest.mark.parametrize(
    "url,output",
    [
        (
            "https://static.openfoodfacts.org/images/products/359/671/046/5248/3.jpg",
            "/359/671/046/5248/3.jpg",
        ),
        (
            "https://static.openfoodfacts.org/images/products/2520549/1.jpg",
            "/2520549/1.jpg",
        ),
    ],
)
def test_get_source_from_ocr_url(url: str, output: str):
    assert get_source_from_ocr_url(url) == output
