"""
This script is used to generate the datasets for the 'neural' category ML
model. For example:
https://github.com/openfoodfacts/openfoodfacts-ai/releases/tag/dataset-category-2020-06-30

Usage: 1. Use 'python -m robotoff download-dataset' to fetch the latest version
of the PO data. 2. Run 'python scripts/category_dataset.py' to construct the
train/test/val datasets,
   alongside the category/ingredient taxonomy dump.
3. Gzip the train/test/val datasets.
4. Upload all of the data (products.json.gz, generated and zipped files under
   'datasets/category/') to
   https://github.com/openfoodfacts/openfoodfacts-ai/releases/ with a
   description of what the data consists of.
"""

import json
import os
from typing import Iterator, Optional

from openfoodfacts.taxonomy import Taxonomy, TaxonomyNode
from sklearn.model_selection import train_test_split

from robotoff import settings
from robotoff.products import ProductDataset, ProductStream
from robotoff.taxonomy import get_taxonomy
from robotoff.types import JSONType
from robotoff.utils import dump_jsonl, get_logger

logger = get_logger()

WRITE_PATH = settings.PROJECT_DIR / "datasets" / "category"


def infer_category_tags(categories: list[str], taxonomy: Taxonomy) -> set[TaxonomyNode]:
    category_nodes = []
    for category_tag in categories:
        if category_tag:
            category_node = taxonomy[category_tag]

            if category_node is not None:
                category_nodes.append(category_node)

    all_categories = set()
    for category_node in category_nodes:
        all_categories.add(category_node)
        all_categories.update(set(category_node.get_parents_hierarchy()))

    return all_categories


def generate_base_dataset(
    category_taxonomy: Taxonomy,
    ingredient_taxonomy: Taxonomy,
    stream: ProductStream,
    lang: Optional[str],
) -> Iterator[JSONType]:
    for product in stream.iter():
        categories_tags: list[str] = product["categories_tags"]
        inferred_categories_tags: list[TaxonomyNode] = list(
            infer_category_tags(categories_tags, category_taxonomy)
        )

        if inferred_categories_tags:
            ingredient_tags = product.get("ingredients_tags", [])
            ingredient_tags = [x for x in ingredient_tags if x]
            known_ingredient_tags = [
                ingredient_tag
                for ingredient_tag in ingredient_tags
                if ingredient_tag in ingredient_taxonomy
            ]
            ingredients_text_field = (
                "ingredients_text_{}".format(lang) if lang else "ingredients_text"
            )
            ingredients_text = product.get(ingredients_text_field, None) or None

            product_name_field = (
                "product_name_{}".format(lang) if lang else "product_name"
            )
            yield {
                "code": product["code"],
                "nutriments": product.get("nutriments") or None,
                "images": product.get("images", {}) or None,
                "product_name": product[product_name_field],
                "categories_tags": [x.id for x in inferred_categories_tags],
                "ingredient_tags": ingredient_tags,
                "known_ingredient_tags": known_ingredient_tags,
                "ingredients_text": ingredients_text,
                "lang": product.get("lang", None),
            }


def generate_train_test_val_datasets(
    category_taxonomy: Taxonomy,
    ingredient_taxonomy: Taxonomy,
    stream: ProductStream,
    lang: Optional[str],
) -> dict[str, Iterator[JSONType]]:
    base_dataset = generate_base_dataset(
        category_taxonomy, ingredient_taxonomy, stream, lang
    )

    train, rem = train_test_split(list(base_dataset), train_size=0.8)
    test, val = train_test_split(rem, train_size=0.5)

    return {"train": train, "test": test, "val": val}


def run(lang: Optional[str] = None):
    logger.info("Generating category dataset for lang %s", lang or "xx")
    dataset = ProductDataset.load()
    training_stream = dataset.stream().filter_nonempty_tag_field("categories_tags")

    if lang is not None:
        training_stream = training_stream.filter_text_field(
            "lang", lang
        ).filter_nonempty_text_field("product_name_{}".format(lang))
    else:
        training_stream = training_stream.filter_nonempty_text_field("product_name")

    os.makedirs(WRITE_PATH, exist_ok=True)

    category_taxonomy = get_taxonomy("category")
    with open(WRITE_PATH / "categories.full.json", "w") as f:
        json.dump(category_taxonomy.to_dict(), f)

    ingredient_taxonomy = get_taxonomy("ingredient")
    with open(WRITE_PATH / "ingredients.full.json", "w") as f:
        json.dump(ingredient_taxonomy.to_dict(), f)

    datasets = generate_train_test_val_datasets(
        category_taxonomy, ingredient_taxonomy, training_stream, lang
    )

    for key, data in datasets.items():
        count = dump_jsonl(
            WRITE_PATH / "category_{}.{}.jsonl".format(lang or "xx", key),
            data,
        )
        logger.info("%s items for dataset %s, lang %s", count, key, lang or "xx")


if __name__ == "__main__":
    # By default generate the complete dataset - if specific language datasets
    # are required, change the list to ('es', 'fr', 'en') etc.
    for lang in (None,):
        run(lang=lang)
