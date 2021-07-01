import typing

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from .constants import (
    FEATURES,
    LABELS_G1,
    LABELS_G2,
    MODEL_G1_FILEPATH,
    MODEL_G2_FILEPATH,
    THRESHOLDS_G1_AS_NP,
    THRESHOLDS_G2_AS_NP,
)
from .types import (
    IngredientDetailed,
    IngredientDetailedList_T,
    PreprocessedX_T,
    XGFoodPrediction,
)


class XGFood:
    """XGFood is a product categorizer based on the product name and ingredients.

    The work has been conducted by a team of students from EMLyon school.

    See the full and detailed readme for more details.
    https://github.com/openfoodfacts/openfoodfacts-ai/tree/develop/ai-emlyon

    The code from the initial XGFood class has been refactored to simplify it.
    In particular, XGFood in Robotoff is meant to be used product per product
    and not on a batch of products directly. This simplifies a lot the
    preprocessing.
    """

    model_G1: typing.Optional[XGBClassifier] = None
    model_G2: typing.Optional[XGBClassifier] = None

    def __init__(self):
        if self.model_G1 is None:
            self.model_G1 = XGBClassifier()
            self.model_G1.load_model(MODEL_G1_FILEPATH)

        if self.model_G2 is None:
            self.model_G2 = XGBClassifier()
            self.model_G2.load_model(MODEL_G2_FILEPATH)

    def predict(
        self, product_name: str, ingredients: IngredientDetailedList_T
    ) -> XGFoodPrediction:
        """Predict the category of a product based on the product name and the list of its ingredients."""
        assert self.model_G1 is not None
        assert self.model_G2 is not None

        X = _preprocess(product_name, ingredients)

        y_probas_G1 = self.model_G1.predict_proba(X)[0]
        pred_G1, conf_G1 = _apply_thresholds(y_probas_G1, tresholds=THRESHOLDS_G1_AS_NP)

        X_G2 = np.append(X, np.array([pred_G1]).reshape(-1, 1), axis=1)
        y_probas_G2 = self.model_G2.predict_proba(X_G2)[0]
        pred_G2, conf_G2 = _apply_thresholds(y_probas_G2, tresholds=THRESHOLDS_G2_AS_NP)

        return {
            "prediction_G1": LABELS_G1[pred_G1],
            "confidence_G1": _to_rounded_float(conf_G1),
            "prediction_G2": LABELS_G2[pred_G2],
            "confidence_G2": _to_rounded_float(conf_G2),
        }


def _preprocess(
    product_name: str, ingredients: IngredientDetailedList_T
) -> pd.DataFrame:
    """Preprocess product by spliting information into 948 features.

    The features consists in 450 most frequent ingredients and 488 most
    frequent words in product_name.
    """
    X: PreprocessedX_T = {column: 0.0 for column in FEATURES}
    _preprocess_ingredients(X, ingredients)
    _preprocess_product_name(X, product_name)
    return pd.DataFrame(X, columns=FEATURES, index=[0])


def _preprocess_ingredients(X: PreprocessedX_T, ingredients: IngredientDetailedList_T):
    for ingredient in ingredients:
        ingredient_name = _clean_ingredient_name(ingredient["text"])
        ingredient_name_with_prefix = "ing_" + ingredient_name
        if X.get(ingredient_name_with_prefix) == 0.0:
            X[ingredient_name_with_prefix] = _get_ingredient_quantity(ingredient)


def _preprocess_product_name(X: PreprocessedX_T, product_name: str):
    product_name = product_name.lower()
    for key in X.keys():
        if not key.startswith("ing_"):
            if key in product_name:
                X[key] = 1.0


def _clean_ingredient_name(ingredient_name: str) -> str:
    return ingredient_name.replace("_", "").replace("-", "").strip("").lower()


def _get_ingredient_quantity(ingredient: IngredientDetailed) -> float:
    for key in ["percent_estimate", "percent_min", "percent_max"]:
        if isinstance(ingredient.get(key), float):
            return ingredient[key]  # type: ignore
    return 1.0


def _apply_thresholds(
    y_probas: np.ndarray, tresholds: typing.List[float]
) -> typing.Tuple[int, float]:
    """Return the prediction along its confidence.

    Thresholds are applied to determine if the highest probability is relevant or not.
    In the case of a predicted value with a too low confidence, the prediction is set
    to "unknown" and the confidence to 0.0.
    """
    result = np.argwhere(y_probas > tresholds)
    if result.size > 0:
        pred = int(result[0])
        return pred, y_probas[pred]
    else:
        return len(tresholds), 0.0


def _to_rounded_float(value: np.float32) -> float:
    return round(float(value), 5)
