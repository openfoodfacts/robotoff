# Package reference

Robotoff is deployed on a web server, but is also distributed as a library.
This document presents a brief, high-level overview of Robotoff’s library primary features. This guide will cover:

- Using OFF dataset
- Using the taxonomies (ingredient, label, category)

## Install

Robotoff is currently compatible with Python 3.11.
Robotoff can be installed [following dev install doc](../how-to-guides/deployment/dev-install.md)

## Play with the Open Food Facts dataset

First, download the dataset: `python -m robotoff download-dataset`

Robotoff includes a set of tools to easily handle the OFF dataset.
As an example, we can print the product name of all complete products from France that have ingredients in French with:

```py
from robotoff.products import ProductDataset

ds = ProductDataset.load()

product_iter = (ds.stream()
                  .filter_by_country_tag('en:france')
                  .filter_nonempty_text_field('ingredients_text_fr')
                  .filter_by_state_tag('en:complete')
                  .iter())

for product in product_iter:
    print(product['product_name'])
```

We first lazily load the dataset using `ProductDataset.load()`.
Then, we create a ProductStream using the `ProductDataset.stream()` method, and apply filters on the stream of products.

The following filters are currently available:

- filter_by_country_tag
- filter_by_state_tag
- filter_nonempty_text_field
- filter_empty_text_field
- filter_nonempty_tag_field
- filter_empty_tag_field
- filter_by_modified_datetime

## Play with the taxonomies

Taxonomies contains items (such as ingredients, labels or categories) organized in a hierarchical way.
Some items are children of other items. For instance, `en:brown-rice` is a child of `en:rice`.

```py
from robotoff.taxonomy import get_taxonomy

# supported taxonomies: ingredient, category, label
taxonomy = get_taxonomy('category')

brown_rice = taxonomy['en:brown-rices']
rice = taxonomy['en:rices']
print(brown_rice)
# Output: <TaxonomyNode en:brown-rices>

print(brown_rice.children)
# Output: [<TaxonomyNode en:brown-jasmine-rices>, <TaxonomyNode en:brown-basmati-rices>]

assert brown_rice.is_child_of(rice)
assert rice.is_parent_of(brown_rice)

assert brown_rice.get_localized_name('fr') == 'Riz complet'

# find_deepest_item takes a list of string as input and outputs a string
deepest_node = taxonomy.find_deepest_nodes([rice, brown_rice])
assert deepest_node == [brown_rice]

print(brown_rice.get_synonyms('fr'))
# Output: ['Riz complet', 'riz cargo', 'riz brun', 'riz semi-complet']

print(brown_rice.get_parents_hierarchy())
# Output: [<TaxonomyNode en:rices>, <TaxonomyNode en:cereal-grains>, <TaxonomyNode en:cereals-and-their-products>, <TaxonomyNode en:cereals-and-potatoes>, <TaxonomyNode en:plant-based-foods>, <TaxonomyNode en:plant-based-foods-and-beverages>, <TaxonomyNode en:seeds>]
```
