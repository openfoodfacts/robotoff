import re
from typing import List

from robotoff.off import OFFAuthentication, get_product, save_ingredients
from robotoff.settings import BaseURLProvider
from robotoff.utils import http_session


def correct_ingredient(
    country: str,
    ingredient: str,
    pattern: str,
    correction: str,
    comment: str,
    auth: OFFAuthentication,
    dry_run: bool = False,
):
    if dry_run:
        print("*** Dry run ***")

    ingredient_field = "ingredients_text_{}".format(country)
    products = list(iter_products(country, ingredient))
    print("{} products".format(len(products)))
    re_patterns = get_patterns(pattern, correction)

    for product in products:
        barcode = product.get("code")
        print(
            "Fixing {}/product/{}".format(
                BaseURLProvider().country(country).get(), barcode
            )
        )
        product = get_product(barcode, fields=[ingredient_field])

        if product is None:
            print("Product not found: {}".format(barcode))
            continue

        ingredients = product[ingredient_field]

        corrected = generate_correction(ingredients, re_patterns)

        if ingredients == corrected:
            print("No modification after correction, skipping")
            continue

        else:
            print(ingredients)
            print(corrected)
            print("-" * 15)

            if not dry_run:
                save_ingredients(
                    barcode, corrected, lang=country, comment=comment, auth=auth
                )


def get_patterns(pattern: str, correction: str) -> List:
    re_patterns = []
    for pattern_string, correction_variant in (
        (pattern, correction),
        (pattern.upper(), correction.upper()),
        (pattern.capitalize(), correction.capitalize()),
    ):
        re_pattern = re.compile(r"(?<!\w){}(?!\w)".format(re.escape(pattern_string)))
        re_patterns.append((re_pattern, correction_variant))

    return re_patterns


def iter_products(country: str, ingredient: str):
    ingredient_field = f"ingredients_text_{country}"
    base_url = BaseURLProvider().country(country).get() + "/ingredient"
    url = base_url + f"/{ingredient}/1.json?fields=code,{ingredient_field}"
    r = http_session.get(url)
    data = r.json()
    count = data["count"]
    page_size = data["page_size"]
    yield from data["products"]

    pages = count // page_size + int(count % page_size != 0)
    for page in range(2, pages):
        url = base_url + f"/{ingredient}/{page}.json?fields=code,{ingredient_field}"
        r = http_session.get(url)
        data = r.json()
        yield from data["products"]


def generate_correction(text: str, patterns: List) -> str:
    for pattern, correction in patterns:
        text = pattern.sub(correction, text)

    return text
