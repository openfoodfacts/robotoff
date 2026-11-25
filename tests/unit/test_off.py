import re

import pytest
import requests

from robotoff.off import get_product_type, get_source_from_url, normalize_tag
from robotoff.types import ProductIdentifier, ServerType


@pytest.mark.parametrize(
    "value,lowercase,expected",
    [
        ("Côtes du Rhône", True, "cotes-du-rhone"),
        ("CÔTES DU RHÔNE", True, "cotes-du-rhone"),
        ("Saint-Émilion", True, "saint-emilion"),
        ("saint-émilion", True, "saint-emilion"),
        ("Châteauneuf-du-Pape", True, "chateauneuf-du-pape"),
        ("éèàù", True, "eeau"),
        ("ÉÈÀÙ", True, "eeau"),
        ("ôâêîç", True, "oaeic"),
        ("ÔÂÊÎÇ", True, "oaeic"),
        ("Saint-Émilion", False, "Saint-Emilion"),
        ("CÔTES DU RHÔNE", False, "COTES-DU-RHONE"),
        ("東京", True, "東京"),
        (" -- Crème & chocolat -- ", True, "creme-chocolat"),
        ("a¹b²c³d", True, "a-b-c-d"),
        ("a&copy;b", True, "a-b"),
        ("", True, ""),
    ],
)
def test_normalize_tag(value: str, lowercase: bool, expected: str) -> None:
    assert normalize_tag(value, lowercase=lowercase) == expected


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


class TestGetProductType:
    def test_get_product_type_no_type_switch(self, requests_mock):
        barcode = "3596710465248"
        requests_mock.get(
            f"https://world.openfoodfacts.net/api/v3.4/product/{barcode}?fields=product_type",
            json={"product": {"product_type": "food"}, "status": "success"},
        )
        new_product_type = get_product_type(
            ProductIdentifier(barcode=barcode, server_type=ServerType.off)
        )
        assert new_product_type == "food"

    def test_get_product_type_product_does_not_exist(self, requests_mock):
        barcode = "3596710465248"
        requests_mock.get(
            f"https://world.openfoodfacts.net/api/v3.4/product/{barcode}?fields=product_type",
            json={
                "errors": [
                    {
                        "field": {"id": "code", "value": barcode},
                        "impact": {
                            "id": "failure",
                            "lc_name": "Failure",
                            "name": "Failure",
                        },
                        "message": {
                            "id": "product_not_found",
                            "lc_name": "",
                            "name": "",
                        },
                    }
                ],
                "status": "failure",
            },
            status_code=404,
        )
        new_product_type = get_product_type(
            ProductIdentifier(barcode=barcode, server_type=ServerType.off)
        )
        assert new_product_type is None

    def test_get_product_type_product_type_switch(self, requests_mock):
        barcode = "3596710465248"
        requests_mock.get(
            f"https://world.openfoodfacts.net/api/v3.4/product/{barcode}?fields=product_type",
            json={
                "errors": [
                    {
                        "field": {"id": "product_type", "value": "beauty"},
                        "impact": {
                            "id": "failure",
                            "lc_name": "Failure",
                            "name": "Failure",
                        },
                        "message": {
                            "id": "product_found_with_a_different_product_type",
                            "lc_name": "",
                            "name": "",
                        },
                    }
                ],
                "status": "failure",
            },
            status_code=404,
        )
        new_product_type = get_product_type(
            ProductIdentifier(barcode=barcode, server_type=ServerType.off)
        )
        assert new_product_type == "beauty"

    def test_get_product_type_http_500_error(self, requests_mock):
        barcode = "3596710465248"
        requests_mock.get(
            f"https://world.openfoodfacts.net/api/v3.4/product/{barcode}?fields=product_type",
            text="Internal Server Error",
            status_code=500,
        )

        with pytest.raises(
            RuntimeError,
            match=re.escape(
                "Unable to get product type (non-200/404 status code): 500, Internal Server Error"
            ),
        ):
            get_product_type(
                ProductIdentifier(barcode=barcode, server_type=ServerType.off)
            )

    def test_get_product_type_timeout(self, requests_mock):
        barcode = "3596710465248"
        requests_mock.get(
            f"https://world.openfoodfacts.net/api/v3.4/product/{barcode}?fields=product_type",
            exc=requests.exceptions.Timeout,
        )

        with pytest.raises(
            RuntimeError,
            match=re.escape("Unable to get product type: error during HTTP request: "),
        ):
            get_product_type(
                ProductIdentifier(barcode=barcode, server_type=ServerType.off)
            )
