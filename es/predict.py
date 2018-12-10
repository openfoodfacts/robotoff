import pandas as pd
import numpy as np

from robotoff.categories import Category, parse_category_json
from robotoff import settings
from ml.ml import import_data

from es.utils import get_es_client
from es.match import predict_category

df = import_data(settings.DATASET_PATH)

category_json = parse_category_json(settings.CATEGORIES_PATH)
category_taxonomy = Category.from_data(category_json)

CATEGORIES_SET = set(category_taxonomy.keys())
CATEGORIES = sorted(CATEGORIES_SET)
CATEGORIES_TO_INDEX = {cat: i for (i, cat) in enumerate(CATEGORIES)}

print("Number of categories: {}".format(len(CATEGORIES)))

fr_df = df[df.countries_tags == 'en:france']

print("Performing prediction on products without categories")
no_cat_df = fr_df[np.logical_and(pd.isnull(fr_df.categories_tags),
                                 pd.notnull(fr_df.product_name))]
print("%d products without categories" % len(no_cat_df))

client = get_es_client()

no_cat_y_pred = []
scores = []

for product_name in no_cat_df.product_name:
    prediction = predict_category(client, product_name)

    if prediction is not None:
        no_cat_y_pred.append(prediction[0])
        scores.append(prediction[1])
    else:
        no_cat_y_pred.append(None)
        scores.append(None)

no_cat_df['predicted_category_tag'] = no_cat_y_pred
no_cat_df['predicted_category_score'] = scores

no_cat_df = no_cat_df[pd.notnull(no_cat_df.predicted_category_tag)]

print("Categories predicted for %d products" % len(no_cat_df))

print("Exporting to JSON")
export_df = no_cat_df.drop(['url', 'generic_name', 'brands_tags',
                            'categories_tags', 'countries_tags',
                            'product_name', 'ingredients_text',
                            'main_category_en'], axis=1)
export_df.to_json('predicted_categories_test.json', orient='records',
                  lines=True)
