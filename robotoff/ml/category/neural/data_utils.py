import dataclasses
from typing import Dict, Iterable, List

import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

from .dataclass import TextPreprocessingConfig
from .preprocess import tokenize, preprocess_product_name

UNK_TOKEN = "<UNK>"


def generate_data(ingredient_tags_iter: Iterable[Iterable[str]],
                  product_name_iter: Iterable[str],
                  ingredient_to_id: Dict,
                  product_name_token_to_int: Dict[str, int],
                  nlp,
                  product_name_max_length: int,
                  product_name_preprocessing_config: TextPreprocessingConfig
                  ) -> List[np.ndarray]:
    ingredient_matrix = process_ingredients(ingredient_tags_iter,
                                            ingredient_to_id).astype(np.float32)
    product_name_matrix = process_product_name(product_name_iter,
                                               nlp=nlp,
                                               token_to_int=product_name_token_to_int,
                                               max_length=product_name_max_length,
                                               preprocessing_config=
                                               product_name_preprocessing_config)
    return [ingredient_matrix, product_name_matrix]


def process_ingredients(ingredients: Iterable[Iterable[str]],
                        ingredient_to_id: Dict[str, int]) -> np.ndarray:
    ingredient_count = len(ingredient_to_id)
    ingredient_binarizer = MultiLabelBinarizer(classes=list(range(ingredient_count)))
    ingredient_int = [[ingredient_to_id[ing]
                       for ing in product_ingredients
                       if ing in ingredient_to_id]
                      for product_ingredients in ingredients]
    return ingredient_binarizer.fit_transform(ingredient_int)


def process_product_name(product_names: Iterable[str],
                         nlp,
                         token_to_int: Dict,
                         max_length: int,
                         preprocessing_config: TextPreprocessingConfig):
    tokens_all = [tokenize(preprocess_product_name(text, **dataclasses.asdict(preprocessing_config)), nlp)
                  for text in product_names]
    tokens_int = [[token_to_int[t if t in token_to_int else UNK_TOKEN] for t in tokens]
                  for tokens in tokens_all]
    return pad_sequences(tokens_int, max_length)
