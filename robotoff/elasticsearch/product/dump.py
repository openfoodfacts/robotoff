import re

from robotoff import settings
from robotoff.ingredients import process_ingredients
from robotoff.products import ProductDataset
from robotoff.utils import get_logger
from robotoff.utils.es import get_es_client, perform_export

logger = get_logger(__name__)


MULTIPLE_SPACES_RE = re.compile(r"\s{2,}")


def product_export():
    dataset = ProductDataset(settings.JSONL_DATASET_PATH)

    product_iter = (
        dataset.stream()
        .filter_by_country_tag("en:france")
        .filter_nonempty_text_field("ingredients_text_fr")
        .filter_by_state_tag("en:complete")
        .iter()
    )
    product_iter = (
        p
        for p in product_iter
        if "ingredients-unknown-score-above-0" not in p.get("quality_tags", [])
    )

    data = (
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

    logger.info("Importing products")

    es_client = get_es_client()
    perform_export(es_client, data, settings.ELASTICSEARCH_PRODUCT_INDEX)


def empty_ingredient(ingredient: str) -> bool:
    return not bool(ingredient.strip(" /-.%0123456789"))


def normalize_ingredient_list(ingredient_text: str):
    ingredients = process_ingredients(ingredient_text)

    normalized = []

    for ingredient in ingredients.iter_normalized_ingredients():
        if empty_ingredient(ingredient):
            continue

        ingredient = MULTIPLE_SPACES_RE.sub(" ", ingredient)
        ingredient = ingredient.strip(" .")
        normalized.append(ingredient)

    return normalized
