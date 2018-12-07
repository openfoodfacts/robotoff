import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.externals import joblib

from sklearn_hierarchical_classification.classifier import HierarchicalClassifier
from sklearn_hierarchical_classification.constants import ROOT
from sklearn_hierarchical_classification.metrics import (h_precision_score,
                                                         h_recall_score,
                                                         h_fbeta_score)

from categories import Category, parse_category_json, generate_category_hierarchy
from ml import import_data, create_base_classifier, create_transformer

TRAIN = False
TRANSFORMER_PATH = 'transformer.joblib'
CLASSIFIER_PATH = 'clf.joblib'

df = import_data("data/en.openfoodfacts.org.products.csv")

category_json = parse_category_json('data/categories.json')
category_taxonomy = Category.from_data(category_json)

CATEGORIES_SET = set(category_taxonomy.keys())
CATEGORIES = sorted(CATEGORIES_SET)
CATEGORIES_TO_INDEX = {cat: i for (i, cat) in enumerate(CATEGORIES)}

category_hierarchy = generate_category_hierarchy(
    category_json, CATEGORIES_TO_INDEX, ROOT)

print("Number of categories: {}".format(len(CATEGORIES)))

fr_df = df[df.countries_tags == 'en:france']
cat_df = df[np.logical_and(df.countries_tags == 'en:france',
                           pd.notnull(df.categories_tags))]


cat_df['deepest_category'] = cat_df.categories_tags.apply(
    lambda categories:
    Category.find_deepest_item(categories, category_taxonomy)
    if any(c in CATEGORIES_SET for c in categories) else np.NaN)

cat_df.dropna(subset=['deepest_category'], inplace=True)

cat_df['deepest_category_int'] = cat_df.deepest_category.apply(
    lambda category: CATEGORIES_TO_INDEX[category])
print(f"{len(df)} elements in original dataframe, "
      f"{len(cat_df)} after category filter")

df_train, df_test = train_test_split(cat_df, random_state=42)
y_train = np.array(list(df_train.deepest_category_int.values))
y_test = np.array(list(df_test.deepest_category_int.values))

if TRAIN:
    print("Training started")
    base_estimator = create_base_classifier()
    transformer = create_transformer()
    classifier = HierarchicalClassifier(base_estimator=base_estimator,
                                        class_hierarchy=category_hierarchy,
                                        prediction_depth='nmlnp',
                                        algorithm='lcpn',
                                        stopping_criteria=0.5)

    X_train = transformer.fit_transform(df_train)
    classifier.fit(X_train, y_train)
    joblib.dump(transformer, TRANSFORMER_PATH)
    joblib.dump(classifier, CLASSIFIER_PATH)
    print("End of training")
else:
    print("Loading model...")
    transformer = joblib.load(TRANSFORMER_PATH)
    classifier = joblib.load(CLASSIFIER_PATH)
    print("Model loaded")

# y_pred = classifier.predict(transformer.transform(df_test))
# report = classification_report(y_test, y_pred,
#                                output_dict=True)

# category_graph = classifier.graph_
# y_test_matrix = np.zeros((y_test.shape[0], len(CATEGORIES_SET)))
# y_test_matrix[np.arange(y_test.shape[0]), y_test] = 1
#
# y_pred_matrix = np.zeros((y_pred.shape[0], len(CATEGORIES_SET)))
# y_pred_matrix[np.arange(y_pred.shape[0]), y_pred] = 1
#
#
# print("Hierachical precision: {},\n"
#       "Hierarchical recall: {}\n"
#       "Hierarchical f-beta: {}".format(h_precision_score(y_test, y_pred, category_graph),
#                                        h_recall_score(y_test, y_pred, category_graph),
#                                        h_fbeta_score(y_test, y_pred, category_graph)))

print("Performing prediction on products without categories")
no_cat_df = fr_df[pd.isnull(fr_df['categories_tags'])]

X_infer = transformer.transform(no_cat_df)
no_cat_y_pred = classifier.predict(X_infer)

no_cat_df['predicted_category_tag'] = [CATEGORIES[i] for i in no_cat_y_pred]

print("Exporting to JSON")
export_df = no_cat_df.drop(['url', 'generic_name', 'brands_tags',
                            'categories_tags', 'countries_tags',
                            'product_name', 'ingredients_text',
                            'main_category_en'], axis=1)
export_df.to_json('predicted_categories.json', orient='records', lines=True)
