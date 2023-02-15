import itertools
from typing import Optional

from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.types import JSONType, NeuralCategoryClassifierModel

from .matcher import predict_by_lang
from .neural.category_classifier import CategoryClassifier


def predict_category(
    product: dict,
    neural_predictor: bool,
    matcher_predictor: bool,
    deepest_only: bool,
    threshold: Optional[float] = None,
    neural_model_name: Optional[NeuralCategoryClassifierModel] = None,
) -> JSONType:
    """Predict categories for a product.

    Two predictors are available:
    - the neural predictor
    - the matcher predictor

    Each predictor can be enabled using their associated flag parameter
    (`neural_predictor` and `matcher_predictor`). This function returns a dict
    where the key is the name of the predictor and the values are lists of
    predicted categories.

    :param product: the product to predict the categories from, should have at
        least `product_name` and `ingredients_tags` fields for neural
        predictor and `product_name_{lang}` and `languages_codes` for matching
        predictor
    :param neural_predictor: if True, add predictions of the neural predictor
    :param matcher_predictor: if True, add predictions of the matcher
        predictor
    :param deepest_only: controls whether the returned list should only
        contain the deepmost categories for a predicted taxonomy chain.
    :param threshold: the score above which we consider the category to be
        detected for neural predictor (default: 0.5)
    :param neural_model_name: the name of the neural model to use to perform
        prediction
    """
    response: JSONType = {}
    taxonomy = get_taxonomy(TaxonomyType.category.name)
    if neural_predictor:
        predictions, debug = CategoryClassifier(taxonomy).predict(
            product, deepest_only, threshold, neural_model_name
        )
        response["neural"] = {
            "predictions": [
                {"value_tag": p.value_tag, "confidence": p.confidence}
                for p in predictions
            ],
            "debug": debug,
        }
    if matcher_predictor:
        predictions = list(
            itertools.chain.from_iterable(predict_by_lang(product).values())
        )

        if deepest_only:
            predicted_dict = {p.value_tag: p for p in predictions}
            taxonomy_nodes = [taxonomy[p.value_tag] for p in predictions]  # type: ignore

            predictions = [
                predicted_dict[x.id]
                for x in taxonomy.find_deepest_nodes(taxonomy_nodes)
            ]

        response["matcher"] = {
            "predictions": [
                {
                    "value_tag": p.value_tag,
                    "debug": {
                        "product_name": p.data["product_name"],
                        "lang": p.data["lang"],
                        "pattern": p.data["pattern"],
                        "processed_product_name": p.data["processed_product_name"],
                        "start_idx": p.data["start_idx"],
                        "end_idx": p.data["end_idx"],
                        "is_full_match": p.data["is_full_match"],
                        "category_name": p.data["category_name"],
                    },
                }
                for p in itertools.chain.from_iterable(
                    predict_by_lang(product).values()
                )
            ]
        }

    return response
