import functools
import numpy as np
from preprocessing import preprocess

from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

import pandas as pd
from spacy.lang.en import English
import Stemmer


fr_stemmer = Stemmer.Stemmer('fr')

class PipelineStore:
    nlp = None
git
    @classmethod
    def get(cls):
        if cls.nlp is None:
            cls.nlp = English()
        
        return cls.nlp


def tokenize(string, stem=False):
    nlp = PipelineStore.get()
    doc = nlp(string)
    tokens = [x.orth_ for x in doc if not x.is_space if len(x.orth_) > 1]

    if stem:
        tokens = fr_stemmer.stemWords(tokens)

    return tokens

def create_classifier(preprocessing_func=None, custom_tokenizer=False):
    preprocessing_func = preprocessing_func or preprocess

    if custom_tokenizer:
        kwargs = {"tokenizer": functools.partial(tokenize, stem=True)}
    else:
        kwargs = {}

    column_trans = ColumnTransformer([
        ('ingredients_vectorizer', CountVectorizer(min_df=5, preprocessor=preprocessing_func, **kwargs), 'ingredients_text'),
        ('product_name_vectorizer', CountVectorizer(min_df=5, preprocessor=preprocessing_func, **kwargs), 'product_name'),
    ])

    classifier = Pipeline([
        ('column_transformer', column_trans),
        ('tfidf', TfidfTransformer()),
        ('clf', OneVsRestClassifier(LogisticRegression()))])
    return classifier


def import_data(path):
    df = pd.read_csv(
        str(path),
        sep='\t',
        usecols=['code', 'url', 'product_name', 'generic_name', 'brands_tags',
                 'categories_tags', 'ingredients_text', 'main_category_en',
                 'countries_tags', 'last_modified_t'],
        dtype={'code': 'str', 'product_name': 'str'},
        converters={'categories_tags': lambda x: x.split(',') if x else np.NaN}
    )
    df = df.fillna(value={'ingredients_text': "", 'product_name': ""})
    return df
