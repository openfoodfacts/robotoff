from typing import Iterator, List, Optional, Set

from robotoff import settings
from robotoff.products import ProductDataset, ProductStream
from robotoff.taxonomy import Taxonomy, TaxonomyNode, get_taxonomy
from robotoff.utils import dump_jsonl, get_logger
from robotoff.utils.types import JSONType

logger = get_logger()


def infer_category_tags(
    categories: List["str"], taxonomy: Taxonomy
) -> Set[TaxonomyNode]:
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


def generate_dataset(stream: ProductStream, lang: Optional[str]) -> Iterator[JSONType]:
    category_taxonomy = get_taxonomy("category")
    ingredient_taxonomy = get_taxonomy("ingredient")

    for product in stream.iter():
        categories_tags: List[str] = product["categories_tags"]
        inferred_categories_tags: List[TaxonomyNode] = list(
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


def run(lang: Optional[str] = None):
    logger.info("Generating category dataset for lang {}".format(lang or "xx"))
    dataset = ProductDataset.load()
    training_stream = dataset.stream().filter_nonempty_tag_field("categories_tags")

    if lang is not None:
        training_stream = training_stream.filter_text_field(
            "lang", lang
        ).filter_nonempty_text_field("product_name_{}".format(lang))
    else:
        training_stream = training_stream.filter_nonempty_text_field("product_name")

    dataset_iter = generate_dataset(training_stream, lang)
    count = dump_jsonl(
        settings.PROJECT_DIR
        / "datasets"
        / "category"
        / "category_{}.jsonl".format(lang or "xx"),
        dataset_iter,
    )
    logger.info("{} items for lang {}".format(count, lang or "xx"))


if __name__ == "__main__":
    for lang in (None, "fr", "it", "en", "de", "es"):
        run(lang=lang)
