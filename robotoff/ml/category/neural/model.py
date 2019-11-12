import operator
import pathlib
from typing import List, Optional, Tuple, Dict, Set

import numpy as np
from tensorflow import keras

from robotoff import settings
from robotoff.ml.category.neural.data_utils import generate_data
from robotoff.ml.category.neural.io import load_config, load_taxonomy, \
    load_ingredient_vocabulary, load_category_vocabulary, load_product_name_vocabulary, \
    load_category_blacklist
from robotoff.ml.networking import http_session, TF_SERVING_BASE_URL
from robotoff.off import get_product
from robotoff.taxonomy import Taxonomy
from robotoff.utils import get_logger
from robotoff.utils.cache import CachedStore
from robotoff.utils.text import get_nlp


logger = get_logger(__name__)


CategoryPrediction = Tuple[str, float]


class BaseModel:
    NAME = 'category'

    def __init__(self, model_path: pathlib.Path):
        self.model_path: pathlib.Path = model_path
        self.model_dir = model_path.parent
        self.config = None
        self.taxonomy = None
        self.category_to_id = None
        self.ingredient_to_id = None
        self.category_names = None
        self.nlp = None
        self.product_name_vocabulary = None
        self.model = None
        self.loaded: bool = False

    def load(self):
        logger.info("Loading model {}".format(self.model_path))
        self.config = load_config(self.model_dir)
        self.taxonomy = load_taxonomy(self.model_dir)
        self.category_to_id = load_category_vocabulary(self.model_dir)
        self.ingredient_to_id = load_ingredient_vocabulary(self.model_dir)
        self.category_names: List[str] = [category for category, _ in
                                          sorted(self.category_to_id.items(),
                                                 key=operator.itemgetter(1))]

        nlp_lang = 'en' if self.config.lang == 'xx' else self.config.lang
        self.nlp = get_nlp(nlp_lang)
        self.product_name_vocabulary = load_product_name_vocabulary(self.model_dir)
        self.loaded = True

    def get_input_from_product(self, product: Dict
                               ) -> Optional[List[np.ndarray]]:
        ingredient_tags = product.get('ingredients_tags', []) or []
        product_name = product.get('product_name', '') or ''

        return generate_data(ingredient_tags=ingredient_tags,
                             product_name=product_name,
                             ingredient_to_id=self.ingredient_to_id,
                             product_name_token_to_int=self.product_name_vocabulary,
                             nlp=self.nlp,
                             product_name_max_length=self.config.model_config.product_name_max_length,
                             product_name_preprocessing_config=self.config.product_name_preprocessing_config)

    @staticmethod
    def process_predictions(y_pred: np.ndarray,
                            category_names: List[str],
                            taxonomy: Taxonomy,
                            threshold: float = 0.5) -> List[CategoryPrediction]:
        y_pred_int = (y_pred > threshold).astype(y_pred.dtype)
        y_pred_int_filled = fill_ancestors(y_pred_int,
                                           taxonomy=taxonomy,
                                           category_names=category_names)

        predicted_categories_ids = y_pred_int_filled[0].nonzero()[0]
        predicted_categories = [category_names[id_] for id_ in predicted_categories_ids]

        predicted = []
        for predicted_category_id, predicted_category in zip(predicted_categories_ids,
                                                             predicted_categories):
            confidence = y_pred[0, predicted_category_id]
            predicted.append((predicted_category, confidence))

        return sorted(predicted, key=operator.itemgetter(1), reverse=True)


class LocalModel(BaseModel):
    def load(self):
        super().load()
        self.model = keras.models.load_model(str(self.model_path))

    def predict_from_barcode(self, barcode: str,
                             deepest_only: bool = False
                             ) -> Optional[List[CategoryPrediction]]:
        product = get_product(barcode, fields=['product_name', 'ingredients_tags'])

        if product is None:
            logger.info("Product {} not found".format(barcode))
            return

        return self.predict_from_product(product, deepest_only=deepest_only)

    def predict_from_product(self, product: Dict,
                             deepest_only: bool = False) -> List[CategoryPrediction]:
        if not self.loaded:
            self.load()

        X = self.get_input_from_product(product)
        y_pred = self.model.predict(X)
        predicted = self.process_predictions(y_pred, self.category_names, self.taxonomy)

        if deepest_only:
            category_to_confidence = dict(predicted)
            predicted = [
                (x.id, category_to_confidence[x.id])
                for x in self.taxonomy.find_deepest_nodes(
                    [self.taxonomy[c] for c, confidence in predicted])
            ]

        return predicted


class RemoteModel(BaseModel):
    def predict_from_barcode(self, barcode: str) -> Optional[List[CategoryPrediction]]:
        if not self.loaded:
            self.load()

        product = get_product(barcode, fields=['product_name', 'ingredients_tags'])

        if product is None:
            logger.info("Product {} not found".format(barcode))
            return

        X = self.get_input_from_product(product)
        X = [X[0].tolist(), X[1].tolist()]

        data = {
            "signature_name": "serving_default",
            "instances": [X]
        }

        r = http_session.post('{}/{}:predict'.format(TF_SERVING_BASE_URL,
                                                     self.NAME),
                              json=data)
        r.raise_for_status()
        response = r.json()

        return response


class ModelRegistry:
    model: Optional[LocalModel] = None

    @classmethod
    def load(cls):
        if cls.model is None:
            cls.model = LocalModel(settings.CATEGORY_CLF_MODEL_PATH)

    @classmethod
    def get(cls) -> LocalModel:
        cls.load()
        return cls.model


def fill_ancestors(y: np.ndarray, taxonomy: Taxonomy,
                   category_to_id: Optional[Dict[str, int]] = None,
                   category_names: Optional[List[str]] = None):
    if category_to_id is None and category_names is None:
        raise ValueError("one of category_to_id, category_names must be provided")

    if category_names is None:
        category_names = [cat for cat, _ in sorted(category_to_id.items(),
                                                   key=operator.itemgetter(1))]
    elif category_to_id is None:
        category_to_id = {cat: i for i, cat in enumerate(category_names)}

    y_ = y.copy()
    for i in range(y_.shape[1]):
        cat_mask = y_[:, i].nonzero()[0]

        if len(cat_mask):
            category_name = category_names[i]
            parents = taxonomy[category_name].get_parents_hierarchy()
            parent_ids = [category_to_id[parent.id] for parent in parents]
            for parent_id in parent_ids:
                y_[cat_mask, parent_id] = 1

    return y_


def predict_from_product(product: Dict,
                         filter_blacklisted: bool = False) -> Optional[List[Dict]]:
    if 'fr' not in product.get('languages_codes', []):
        logger.debug("fr is not one on product languages, skipping category detection")
        return

    product_name = product.get('product_name', '') or ''

    if not product_name:
        logger.debug("No product name, skipping category detection")
        return

    model = ModelRegistry.get()
    predictions = model.predict_from_product(product, deepest_only=True)

    if filter_blacklisted:
        predictions = filter_blacklisted_categories(predictions)

    return format_predictions(product, predictions, 'fr')


def format_predictions(product: Dict,
                       predictions: List[CategoryPrediction],
                       lang: str) -> List[Dict]:
    formatted_predictions = []

    for category, confidence in predictions:
        formatted = {
            'barcode': product['code'],
            'category': category,
            'lang': lang,
            'model': 'neural',
            'confidence': confidence,
        }
        formatted_predictions.append(formatted)

    return formatted_predictions


def filter_blacklisted_categories(predictions: List[CategoryPrediction]
                                  ) -> List[CategoryPrediction]:
    category_blacklist: Set[str] = CATEGORY_BLACKLIST_STORE.get()
    return [
        (category, confidence)
        for (category, confidence) in predictions
        if category not in category_blacklist
    ]


CATEGORY_BLACKLIST_STORE = CachedStore(load_category_blacklist)
