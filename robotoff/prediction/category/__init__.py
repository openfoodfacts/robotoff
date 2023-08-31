from typing import Optional

from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.types import JSONType, NeuralCategoryClassifierModel, ProductIdentifier

from .neural.category_classifier import CategoryClassifier


def predict_category(
    product: dict,
    product_id: ProductIdentifier,
    deepest_only: bool,
    threshold: Optional[float] = None,
    neural_model_name: Optional[NeuralCategoryClassifierModel] = None,
    clear_cache: bool = False,
) -> JSONType:
    """Predict categories for a product using neural model.

    This function returns a dict where the key is the name of the predictor
    and the values are lists of predicted categories.

    :param product: the product to predict the categories from, see
        `CategoryClassifier.predict` for expected fields.
    :param product_id: identifier of the product
    :param deepest_only: controls whether the returned list should only
        contain the deepmost categories for a predicted taxonomy chain.
    :param threshold: the score above which we consider the category to be
        detected for neural predictor (default: 0.5)
    :param neural_model_name: the name of the neural model to use to perform
        prediction
    :param clear_cache: if True, clear ingredient processing cache of neural
        model before returning results
    """
    taxonomy = get_taxonomy(TaxonomyType.category.name)
    predictions, debug = CategoryClassifier(taxonomy).predict(
        product,
        product_id,
        deepest_only,
        threshold,
        neural_model_name,
        clear_cache=clear_cache,
    )
    return {
        "neural": {
            "predictions": [
                {"value_tag": p.value_tag, "confidence": p.confidence}
                for p in predictions
            ],
            "debug": debug,
        }
    }
