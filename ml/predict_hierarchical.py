import pandas as pd

from sklearn.externals import joblib
import networkx as nx
from sklearn_hierarchical_classification.constants import ROOT

from robotoff.products import ProductDataset
from robotoff.taxonomy import TAXONOMY_STORES, TaxonomyType, Taxonomy

category_taxonomy: Taxonomy = TAXONOMY_STORES[TaxonomyType.category.name].get()

TRANSFORMER_PATH = 'transformer.joblib'
CLASSIFIER_PATH = 'clf.joblib'

dataset: ProductDataset = ProductDataset.load()
CATEGORIES_SET = set(category_taxonomy.keys())
CATEGORIES = sorted(CATEGORIES_SET)
CATEGORIES_TO_INDEX = {cat: i for (i, cat) in enumerate(CATEGORIES)}

print("Number of categories: {}".format(len(CATEGORIES)))

predict_dataset_iter = (dataset.stream()
                               .filter_by_country_tag('en:france')
                               .filter_empty_tag_field('categories_tags'))

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
