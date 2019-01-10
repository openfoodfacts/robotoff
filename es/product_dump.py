import hashlib
import re
from typing import List, Union

from robotoff.products import ProductDataset
from robotoff import settings

from robotoff.utils.es import get_es_client, perform_export


PUNCTUATION_RE = re.compile(r"[()_,.:;\[\]|`\\{}]")
MULTIPLE_SPACES_RE = re.compile(r"\s{2,}")
BLACKLIST_INGREDIENT_RE = re.compile(r"[-•]|\d{1,2}(?:,\d+)?\s*%")


def normalize_ingredient(ingredient: str):
    ingredient = PUNCTUATION_RE.sub(' ', ingredient)
    ingredient = MULTIPLE_SPACES_RE.sub(' ', ingredient)
    ingredient = ingredient.strip()

    if BLACKLIST_INGREDIENT_RE.match(ingredient):
        return None

    return ingredient


def normalize_ingredient_list(ingredients: List[Union[str, None]]):
    normalized = []

    for ingredient in ingredients:
        if ingredient is None:
            continue

        normalized_ingredient = normalize_ingredient(ingredient)

        if normalized_ingredient:
            normalized.append(normalized_ingredient)

    return normalized


dataset = ProductDataset(settings.JSONL_DATASET_PATH)

product_iter = (dataset.stream()
                       .filter_by_country_tag('en:france')
                       .filter_nonempty_text_field('ingredients_text_fr')
                       .filter_nonempty_tag_field('ingredients_debug')
                       .filter_by_state_tag('en:complete')
                       .iter())
data = ((hashlib.sha256(product['code'].encode('utf-8')).hexdigest(),
         {'ingredients_text_fr': normalize_ingredient_list(product['ingredients_debug'])})
        for product in product_iter)

print("Importing products")

es_client = get_es_client()
perform_export(es_client, data, settings.ELASTICSEARCH_PRODUCT_INDEX)
