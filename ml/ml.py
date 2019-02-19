from typing import List

from ml.preprocessing import preprocess

from sklearn.linear_model import LogisticRegression

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


def create_base_classifier():
    return Pipeline([
        ('tfidf', TfidfTransformer()),
        ('clf', LogisticRegression())])


def ingredient_preprocess(ingredients_tags: List[str]) -> str:
    return ' '.join(ingredients_tags)


def create_transformer(preprocessing_func=None, **kwargs):
    preprocessing_func = preprocessing_func or preprocess

    return ColumnTransformer([
        ('ingredients_vectorizer',
         CountVectorizer(min_df=5,
                         preprocessor=ingredient_preprocess,
                         analyzer='word',
                         token_pattern=r"[a-zA-Z-:]+",
                         **kwargs), 'ingredients_tags'),
        ('product_name_vectorizer',
         CountVectorizer(min_df=5,
                         preprocessor=preprocessing_func,
                         **kwargs), 'product_name'),
    ])

