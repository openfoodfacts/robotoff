import itertools
import re
from typing import Dict, Iterator, List

from robotoff.ingredients import process_ingredients, FR_KNOWN_TOKENS
from robotoff.products import ProductDataset
from robotoff import settings
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.es import get_es_client, perform_export
from robotoff.utils.text import FR_NLP_CACHE


logger = get_logger(__name__)


MULTIPLE_SPACES_RE = re.compile(r"\s{2,}")


def ingredients_iter() -> Iterator[str]:
    known_tokens = FR_KNOWN_TOKENS.get()
    nlp = FR_NLP_CACHE.get()

    for ingredient in text_file_iter(settings.INGREDIENTS_FR_PATH):
        if all(token.lower_ in known_tokens for token in nlp(ingredient)):
            yield ingredient


def product_export(version: str = "product"):
    dataset = ProductDataset(settings.JSONL_DATASET_PATH)

    product_stream = (
        dataset.stream()
        .filter_text_field("lang", "fr")
        .filter_by_country_tag("en:france")
        .filter_nonempty_text_field("ingredients_text_fr")
    )

    if "all" not in version:
        product_stream = product_stream.filter_by_state_tag("en:complete")

    product_iter = product_stream.iter()
    product_iter = (
        p for p in product_iter if int(p.get("unknown_ingredients_n", 0)) == 0
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

    if "extended" in version:
        ingredients = (
            (
                "ingredient_{}".format(i),
                {"ingredients_text_fr": normalize_ingredient_list(ingredient)},
            )
            for i, ingredient in enumerate(ingredients_iter())
        )
        iterator: Iterator = itertools.chain(data, ingredients)

    else:
        iterator = data

    index = version
    es_client = get_es_client()
    logger.info("Deleting products")
    delete_products(es_client, index)
    logger.info("Importing products")
    inserted = perform_export(es_client, iterator, index)
    logger.info("{} rows inserted".format(inserted))


def empty_ingredient(ingredient: str) -> bool:
    return not bool(ingredient.strip(" /-.%0123456789"))


def normalize_ingredient_list(ingredient_text: str) -> List[str]:
    ingredients = process_ingredients(ingredient_text)

    normalized = []

    for ingredient in ingredients.iter_normalized_ingredients():
        if empty_ingredient(ingredient):
            continue

        ingredient = MULTIPLE_SPACES_RE.sub(" ", ingredient)
        ingredient = ingredient.strip(" .")
        normalized.append(ingredient)

    return normalized


def delete_products(client, index_name: str):
    body: Dict = {"query": {"match_all": {}}}
    client.delete_by_query(
        body=body, index=index_name, doc_type=settings.ELASTICSEARCH_TYPE,
    )
