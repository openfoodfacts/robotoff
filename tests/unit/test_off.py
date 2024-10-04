import pytest

from robotoff.off import get_source_from_url


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
        (
            "https://static.openfoodfacts.org/images/products/2520549/1.json",
            "/2520549/1.jpg",
        ),
    ],
)
def test_get_source_from_url(url: str, output: str):
    assert get_source_from_url(url) == output
