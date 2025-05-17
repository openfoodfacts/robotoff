import typing
from collections import Counter

import tqdm

from robotoff.products import ProductDataset
from robotoff.taxonomy import Taxonomy, TaxonomyType, get_taxonomy


def infer_missing_category_tags(
    category_tags: list[str], taxonomy: Taxonomy
) -> set[str]:
    all_categories: set[str] = set()
    for category_tag in category_tags:
        category_node = taxonomy[category_tag]
        if category_node:
            all_categories.add(category_node.id)
            all_categories |= set(x.id for x in category_node.get_parents_hierarchy())
    return all_categories


ds = ProductDataset.load()
taxonomy = get_taxonomy(TaxonomyType.category.name)

counter: typing.Counter = Counter()
all_counter: typing.Counter = Counter()
for product in tqdm.tqdm(ds.stream().iter_product()):
    if not product.categories_tags:
        continue

    category_tags = list(infer_missing_category_tags(product.categories_tags, taxonomy))
    all_counter.update(category_tags)
    category_tag_nodes = [taxonomy[category_tag] for category_tag in category_tags]
    deepest_nodes = taxonomy.find_deepest_nodes(category_tag_nodes)
    generic_categories = [
        node.id for node in category_tag_nodes if node not in deepest_nodes
    ]
    counter.update(generic_categories)

percents = {}
for item, count in counter.most_common():
    percents[item] = count / all_counter[item]

for item, percent in sorted(percents.items(), key=lambda x: x[1], reverse=True):
    all_count = all_counter[item]
    if all_count >= 10_000 and percent >= 0.8:
        print(f"{item}: {percent} (all count: {all_count})")
