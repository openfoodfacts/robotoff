from typing import List, Optional

import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.externals import joblib

from sklearn_hierarchical_classification.classifier import HierarchicalClassifier
from sklearn_hierarchical_classification.constants import ROOT
# from sklearn_hierarchical_classification.metrics import (h_precision_score,
#                                                          h_recall_score,
#                                                          h_fbeta_score)
from sklearn.metrics import classification_report

from robotoff.products import ProductDataset
from robotoff.taxonomy import Taxonomy, TAXONOMY_STORES, TaxonomyType, \
    generate_category_hierarchy
from ml.ml import create_base_classifier, create_transformer

TRAIN = False
TRANSFORMER_PATH = 'transformer.joblib'
CLASSIFIER_PATH = 'clf.joblib'
CATEGORY_LABELS_PATH = 'category_labels.txt'

category_taxonomy: Taxonomy = TAXONOMY_STORES[TaxonomyType.category.name].get()
CATEGORIES_SET = set(category_taxonomy.keys())
CATEGORIES = sorted(CATEGORIES_SET)
CATEGORIES_TO_INDEX = {cat: i for (i, cat) in enumerate(CATEGORIES)}
category_hierarchy = generate_category_hierarchy(category_taxonomy,
                                                 CATEGORIES_TO_INDEX,
                                                 ROOT)

print("Number of categories: {}".format(len(CATEGORIES)))

dataset: ProductDataset = ProductDataset.load()
training_dataset_iter = (dataset.stream()
                                .filter_by_country_tag('en:france')
                                .filter_nonempty_text_field('product_name')
                                .filter_nonempty_tag_field('ingredients_tags')
                                .filter_nonempty_tag_field('categories_tags'))


training_dataset = []

processed = 0
for item in training_dataset_iter:
    processed += 1
    categories_tags: List[str] = item['categories_tags']
    deepest_category: Optional[str] = category_taxonomy.find_deepest_item(
        categories_tags)

    if deepest_category is None:
        continue

    training_sample = {
        'barcode': item['code'],
        'deepest_category': deepest_category,
        'deepest_category_int': CATEGORIES_TO_INDEX[deepest_category],
        'ingredients_tags': item['ingredients_tags'],
        'product_name': item['product_name'],
    }
    training_dataset.append(training_sample)


df = pd.DataFrame(training_dataset)

print("{} elements in original dataframe, {} after category "
      "filter".format(processed, len(training_dataset)))

train_df, test_df = train_test_split(df, random_state=42)
y_train = train_df.deepest_category_int.values
y_test = test_df.deepest_category_int.values

print("Training started")
base_estimator = create_base_classifier()
transformer = create_transformer()
classifier = HierarchicalClassifier(base_estimator=base_estimator,
                                    class_hierarchy=category_hierarchy,
                                    prediction_depth='nmlnp',
                                    algorithm='lcpn',
                                    stopping_criteria=0.5)

X_train = transformer.fit_transform(train_df)
classifier.fit(X_train, y_train)
joblib.dump(transformer, TRANSFORMER_PATH)
joblib.dump(classifier, CLASSIFIER_PATH)

with open(CATEGORY_LABELS_PATH, 'w') as f:
    for category in CATEGORIES:
        f.write('{}\n'.format(category))

print("End of training")

y_pred = classifier.predict(transformer.transform(test_df))
report = classification_report(y_test, y_pred)

category_graph = classifier.graph_
y_test_matrix = np.zeros((y_test.shape[0], len(CATEGORIES_SET)))
y_test_matrix[np.arange(y_test.shape[0]), y_test] = 1

y_pred_matrix = np.zeros((y_pred.shape[0], len(CATEGORIES_SET)))
y_pred_matrix[np.arange(y_pred.shape[0]), y_pred] = 1


print("Hierachical precision: {},\n"
      "Hierarchical recall: {}\n"
      "Hierarchical f-beta: {}".format(h_precision_score(y_test, y_pred, category_graph),
                                       h_recall_score(y_test, y_pred, category_graph),
                                       h_fbeta_score(y_test, y_pred, category_graph)))
