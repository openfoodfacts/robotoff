import pytest

from robotoff.metrics import get_facet_name


@pytest.mark.parametrize(
    "url,expected_facet_name",
    [
        ("https://world.openfoodfacts.org/facets/states?json=1", "states"),
        ("https://world.openfoodfacts.org/facets/data-quality?json=1", "data_quality"),
        (
            "https://world.openfoodfacts.org/facets/entry-date/2024-01-01/contributors?json=1",
            "contributors",
        ),
        ("https://world.openfoodfacts.org/facets/brands.json", "brands.json"),
    ],
)
def test_get_facet_name(url: str, expected_facet_name: str):
    assert get_facet_name(url) == expected_facet_name
