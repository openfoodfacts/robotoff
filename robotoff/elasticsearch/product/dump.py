"""Methods to load products in elasticsearch
"""
import re
from typing import Iterable

from robotoff import settings
from robotoff.products import ProductDataset
from robotoff.spellcheck.items import Ingredients
from robotoff.utils import get_logger

logger = get_logger(__name__)


MULTIPLE_SPACES_RE = re.compile(r"\s{2,}")


def generate_product_data() -> Iterable[tuple[str, dict]]:
    dataset = ProductDataset(settings.JSONL_DATASET_PATH)

    product_stream = (
        dataset.stream()
        .filter_text_field("lang", "fr")
        .filter_by_country_tag("en:france")
        .filter_nonempty_text_field("ingredients_text_fr")
        .filter_by_state_tag("en:complete")
    )

    product_iter = product_stream.iter()
    product_iter = (
        p for p in product_iter if int(p.get("unknown_ingredients_n", 0)) == 0
    )

    return (
        (
            product["code"],
            {
                "ingredients_text_fr": normalize_ingredient_list(
                    product["ingredients_text_fr"]
                )
            },
        )
        for product in product_iter
    )


def empty_ingredient(ingredient: str) -> bool:
    return not bool(ingredient.strip(" /-.%0123456789"))


def normalize_ingredient_list(ingredient_text: str) -> list[str]:
    ingredients = Ingredients.from_text(ingredient_text)

    normalized = []

    for ingredient in ingredients.get_iter():
        if empty_ingredient(ingredient):
            continue

        ingredient = MULTIPLE_SPACES_RE.sub(" ", ingredient)
        ingredient = ingredient.strip(" .")
        normalized.append(ingredient)

    return normalized
