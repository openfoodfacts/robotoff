from collections import Counter

import pandas as pd
import numpy as np
from more_itertools import flatten


def import_data(path):
    return pd.read_csv(
        str(path),
        sep='\t',
        usecols=['code', 'url', 'product_name', 'generic_name', 'brands_tags',
                 'categories_tags', 'ingredients_text', 'main_category_en',
                 'countries_tags'],
        dtype={'code': 'str', 'product_name': 'str'},
        converters={'categories_tags': lambda x: x.split(',') if x else np.NaN}
    )


df = import_data("data/en.openfoodfacts.org.products.csv")
df = df[pd.notnull(df['categories_tags'])]
df = df[pd.notnull(df['ingredients_text'])]
fr_df = df[df['countries_tags'] == 'en:france']

categories_counter = Counter(flatten(c for c in fr_df['categories_tags']))
