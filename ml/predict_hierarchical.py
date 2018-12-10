import pandas as pd

from sklearn.externals import joblib
import networkx as nx
from sklearn_hierarchical_classification.constants import ROOT

from robotoff.categories import Category, parse_category_json, generate_category_hierarchy
from ml import import_data

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

print("Loading model...")
transformer = joblib.load(TRANSFORMER_PATH)
classifier = joblib.load(CLASSIFIER_PATH)
print("Model loaded")


print("Performing prediction on products without categories")
no_cat_df = fr_df[pd.isnull(fr_df['categories_tags'])]

X_infer = transformer.transform(no_cat_df)
no_cat_y_pred = classifier.predict(X_infer)

no_cat_df['predicted_category_tag'] = [CATEGORIES[i] for i in no_cat_y_pred]

graph = classifier.graph_
no_cat_df['category_depth'] = [
    len(nx.shortest_path(classifier.graph_, ROOT, i)) - 2
    for i in no_cat_y_pred
]


print("Exporting to JSON")
export_df = no_cat_df.drop(['url', 'generic_name', 'brands_tags',
                            'categories_tags', 'countries_tags',
                            'product_name', 'ingredients_text',
                            'main_category_en'], axis=1)
export_df.to_json('predicted_categories.json', orient='records', lines=True)
