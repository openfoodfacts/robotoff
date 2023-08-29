# Category Prediction

Knowing the category of each product is critically important at Open Food Facts, as category is used to compute Nutriscore, to assess the environmental impact of the product (thanks to Agribalyse database), to compare the product to similar ones,...

In Open Food Facts, more 12,500 categories exist in the [category taxonomy](https://static.openfoodfacts.org/data/taxonomies/categories.full.json) (as of March 2023). Category prediction using product meta-data was one the first project developed as part of Robotoff in 2018.

A neural network model is used to predict categories [^neural]. Details about the model training, results and model assets are available on the [model robotoff-models release page](https://github.com/openfoodfacts/robotoff-models/releases/tag/keras-category-classifier-image-embeddings-3.0). 

This model takes as inputs (all inputs are optional):

- the product name (`product_name` field)
- the ingredient list (`ingredients` field): only the ingredients of depth one are considered (sub-ingredients are ignored)
- the ingredients extracted from OCR texts: all OCR results are fetched and ingredients present in the taxonomy are detected using [flashtext library](https://flashtext.readthedocs.io/en/latest/).
- the most common nutriments: salt, proteins, fats, saturated fats, carbohydrates, energy,...
- up to the most 10 recent images: we generate an embedding for each image using [clip-vit-base-patch32](https://github.com/openfoodfacts/robotoff-models/releases/tag/clip-vit-base-patch32) model, and generate a single vector using a multi-head attention layer + GlobalAveragePooling1d.

The model was trained to predict a subset of all categories: broad categories (such as plant based foods and beverages) were discarded to keep only the most informative categories, and categories with less than 10 products were ignored. The model can predict categories for about 3,500 categories of the taxonomy.

For each predicted category, we also fetch the prediction score of parents, children and siblings (node with the same parents) categories in the taxonomy. This will be used soon to display predictions about neighbor categories and select a more (or less) specific category on Hunger Games if needed.

We also [computed for each category](https://github.com/openfoodfacts/robotoff-models/releases/download/keras-category-classifier-image-embeddings-3.0/threshold_report_0.99.json) the detection threshold above which we have a `precision >= 0.99` on the split obtained from merging validation and test sets. For these predictions, we have a very high confidence that the predicted category is correct. We always generate insights from these *above-threshold predictions* (except if the category is already filled in for the product), and the `v3_categorizer_automatic_processing` campaign is added to the insight.

The Hunger Game annotation campaign can be [accessed here](https://hunger.openfoodfacts.org/questions?type=category&campaign=v3_categorizer_automatic_processing). If the experiment is successful (`precision >= 0.99` on Hunger Games questions), we will turn on automatic categorization on *above-threshold predictions*.

## Changelog

Here is a summary on the milestones in category detection:

- 2018-12 | Deployment of the first "matching" categorizer based on Elasticsearch
- 2019-02 | Deployment of the first hierarchical category classifier using scikit-learn
- 2019-11 | Deployment of the [first neural model (v1)](https://github.com/openfoodfacts/robotoff-models/releases/tag/keras-category-classifier-xx-1.0) for product categorization, hierarchical classification was disabled.
- 2021-12 | Deployment of the [v2 model](https://github.com/openfoodfacts/robotoff-models/releases/tag/keras-category-classifier-xx-2.0)
- 2022-01 |  Automatic processing of all category predictions with `score >= 0.9`
- 2022-03 | [Disable automatic processing of categories](https://github.com/openfoodfacts/robotoff/issues/636)
- 2022-10 | Remove Elasticsearch-based category predictor, switch to custom model in Robotoff codebase

- 2023-03 | Deployment of the [v3 model](https://github.com/openfoodfacts/robotoff-models/releases/tag/keras-category-classifier-image-embeddings-3.0)
- 2023-08 | Disabling of the `matcher` predictor: after an analysis through Hunger Games, most errors were due to the `matcher` predictor, and the `neural` predictor gave most of the time accurate predictions for products for which the `matcher` predictor failed.

[^neural]: see `robotoff.prediction.category.neural`