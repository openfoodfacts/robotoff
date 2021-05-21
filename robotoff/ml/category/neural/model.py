import operator
import pathlib
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np
from more_itertools import chunked
from tensorflow import keras

from robotoff import settings
from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import ProductInsights, RawInsight
from robotoff.ml.category.neural.data_utils import generate_data
from robotoff.ml.category.neural.io import (
    load_category_blacklist,
    load_category_vocabulary,
    load_config,
    load_ingredient_vocabulary,
    load_product_name_vocabulary,
    load_taxonomy,
)
from robotoff.off import get_product
from robotoff.taxonomy import Taxonomy
from robotoff.utils import get_logger, http_session
from robotoff.utils.cache import CachedStore
from robotoff.utils.text import get_nlp

logger = get_logger(__name__)


CategoryPrediction = Tuple[str, float]


class BaseModel:
    NAME = "category"

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
        self.category_names: List[str] = [
            category
            for category, _ in sorted(
                self.category_to_id.items(), key=operator.itemgetter(1)
            )
        ]

        nlp_lang = "en" if self.config.lang == "xx" else self.config.lang
        self.nlp = get_nlp(nlp_lang)
        self.product_name_vocabulary = load_product_name_vocabulary(self.model_dir)
        self.loaded = True

    def get_input_from_products(self, products: Iterable[Dict]) -> List[np.ndarray]:
        ingredient_tags = [
            product.get("ingredients_tags", []) or [] for product in products
        ]
        product_name = [product.get("product_name", "") or "" for product in products]

        return generate_data(
            ingredient_tags_iter=ingredient_tags,
            product_name_iter=product_name,
            ingredient_to_id=self.ingredient_to_id,  # type: ignore
            product_name_token_to_int=self.product_name_vocabulary,  # type: ignore
            nlp=self.nlp,
            product_name_max_length=self.config.model_config.product_name_max_length,  # type: ignore
            product_name_preprocessing_config=self.config.product_name_preprocessing_config,  # type: ignore
        )

    @staticmethod
    def process_predictions(
        y_pred: np.ndarray,
        category_names: List[str],
        taxonomy: Taxonomy,
        threshold: float = 0.5,
        deepest_only: bool = False,
    ) -> List[List[CategoryPrediction]]:
        y_pred_int = (y_pred > threshold).astype(y_pred.dtype)
        y_pred_int_filled = fill_ancestors(
            y_pred_int, taxonomy=taxonomy, category_names=category_names
        )

        predicted = []
        for i in range(y_pred_int_filled.shape[0]):
            predicted_categories_ids = y_pred_int_filled[i].nonzero()[0]
            predicted_categories = [
                category_names[id_] for id_ in predicted_categories_ids
            ]

            product_predicted = []
            for predicted_category_id, predicted_category in zip(
                predicted_categories_ids, predicted_categories
            ):
                confidence = y_pred[i, predicted_category_id]
                product_predicted.append((predicted_category, float(confidence)))

            product_predicted = sorted(
                product_predicted, key=operator.itemgetter(1), reverse=True
            )

            if deepest_only:
                category_to_confidence = dict(product_predicted)
                product_predicted = [
                    (x.id, category_to_confidence[x.id])
                    for x in taxonomy.find_deepest_nodes(
                        [taxonomy[c] for c, confidence in product_predicted]
                    )
                ]
            predicted.append(product_predicted)

        return predicted


class LocalModel(BaseModel):
    def load(self):
        super().load()
        self.model = keras.models.load_model(str(self.model_path))

    def predict_from_barcode(
        self, barcode: str, deepest_only: bool = False
    ) -> Optional[List[CategoryPrediction]]:
        product = get_product(barcode, fields=["product_name", "ingredients_tags"])

        if product is None:
            logger.info("Product {} not found".format(barcode))
            return None

        return self.predict_from_product(product, deepest_only=deepest_only)

    def predict_from_product(
        self, product: Dict, deepest_only: bool = False
    ) -> List[CategoryPrediction]:
        return self.predict_from_product_batch([product], deepest_only)[0]

    def predict_from_product_batch(
        self, products: Iterable[Dict], deepest_only: bool = False
    ) -> List[List[CategoryPrediction]]:
        if not self.loaded:
            self.load()

        X = self.get_input_from_products(products)
        y_pred = self.model.predict(X)  # type: ignore
        return self.process_predictions(
            y_pred, self.category_names, self.taxonomy, deepest_only=deepest_only  # type: ignore
        )


class RemoteModel(BaseModel):
    def predict_from_barcode(self, barcode: str) -> Optional[List[CategoryPrediction]]:
        if not self.loaded:
            self.load()

        product = get_product(barcode, fields=["product_name", "ingredients_tags"])

        if product is None:
            logger.info("Product {} not found".format(barcode))
            return None

        X = self.get_input_from_products([product])[0]
        X = [X[0].tolist(), X[1].tolist()]  # type: ignore

        data = {"signature_name": "serving_default", "instances": [X]}

        r = http_session.post(
            "{}/{}:predict".format(settings.TF_SERVING_BASE_URL, self.NAME), json=data
        )
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
        return cls.model  # type: ignore


def fill_ancestors(
    y: np.ndarray,
    taxonomy: Taxonomy,
    category_to_id: Optional[Dict[str, int]] = None,
    category_names: Optional[List[str]] = None,
):
    if category_to_id is None and category_names is None:
        raise ValueError("one of category_to_id, category_names must be provided")

    if category_names is None:
        category_names = [
            cat for cat, _ in sorted(category_to_id.items(), key=operator.itemgetter(1))  # type: ignore
        ]
    elif category_to_id is None:
        category_to_id = {cat: i for i, cat in enumerate(category_names)}

    y_ = y.copy()
    for i in range(y_.shape[1]):
        cat_mask = y_[:, i].nonzero()[0]

        if len(cat_mask):
            category_name = category_names[i]
            parents = taxonomy[category_name].get_parents_hierarchy()
            parent_ids = [category_to_id[parent.id] for parent in parents]  # type: ignore
            for parent_id in parent_ids:
                y_[cat_mask, parent_id] = 1

    return y_


def predict_from_product(
    product: Dict,
    allowed_lang: Optional[Set[str]] = None,
    filter_blacklisted: bool = False,
) -> Optional[ProductInsights]:
    if not keep_product(product, allowed_lang):
        return None

    model = ModelRegistry.get()
    predictions = model.predict_from_product(product, deepest_only=True)

    if filter_blacklisted:
        predictions = filter_blacklisted_categories(predictions)

    return format_predictions(product, predictions, "xx")


def keep_product(product: Dict, allowed_lang: Optional[Set[str]] = None) -> bool:
    product_languages = set(product.get("languages_codes", []))

    if allowed_lang is not None and not allowed_lang.intersection(product_languages):
        logger.debug("fr is not one on product languages, skipping category detection")
        return False

    product_name = product.get("product_name", "") or ""

    if not product_name:
        logger.debug("No product name, skipping category detection")
        return False

    return True


def predict_from_product_batch(
    product_iter: Iterable[Dict],
    allowed_lang: Optional[Iterable[str]] = None,
    filter_blacklisted: bool = False,
    batch_size: int = 32,
) -> Iterable[ProductInsights]:
    model = ModelRegistry.get()
    allowed_lang = set(allowed_lang) if allowed_lang else set()

    filtered_product_iter = (p for p in product_iter if keep_product(p, allowed_lang))

    for product_batch in chunked(filtered_product_iter, batch_size):
        predictions_batch = model.predict_from_product_batch(
            product_batch, deepest_only=True
        )

        if filter_blacklisted:
            predictions_batch = [
                filter_blacklisted_categories(predictions)
                for predictions in predictions_batch
            ]

        for predictions, product in zip(predictions_batch, product_batch):
            yield format_predictions(product, predictions, "xx")


def format_predictions(
    product: Dict, predictions: List[CategoryPrediction], lang: str
) -> ProductInsights:
    insights = []

    for category, confidence in predictions:
        insights.append(
            RawInsight(
                type=InsightType.category,
                value_tag=category,
                data={"lang": lang, "model": "neural", "confidence": confidence},
            )
        )

    return ProductInsights(
        barcode=product["code"], type=InsightType.category, insights=insights
    )


def filter_blacklisted_categories(
    predictions: List[CategoryPrediction],
) -> List[CategoryPrediction]:
    category_blacklist: Set[str] = CATEGORY_BLACKLIST_STORE.get()
    return [
        (category, confidence)
        for (category, confidence) in predictions
        if category not in category_blacklist
    ]


CATEGORY_BLACKLIST_STORE = CachedStore(load_category_blacklist)
