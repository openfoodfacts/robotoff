from typing import Optional

from robotoff import settings
from robotoff.types import JSONType, NeuralCategoryClassifierModel
from robotoff.utils import http_session


def predict(
    product: dict, threshold: Optional[float] = None
) -> tuple[list[tuple[str, float]], JSONType]:
    """Returns an unordered list of category predictions for the given
    product.

    :param product: the product to predict the categories from, should
    have at least `product_name` and `ingredients_tags` fields
    :param deepest_only: controls whether the returned list should only
    contain the deepmost categories for a predicted taxonomy chain.

        For example, if we predict 'fresh vegetables' -> 'legumes' ->
        'beans' for a product,
        setting deepest_only=True will return ['beans'].
    :param threshold: the score above which we consider the category to be
    detected (default: 0.5)
    """
    if threshold is None:
        threshold = 0.5

    debug: JSONType = {
        "model_name": NeuralCategoryClassifierModel.keras_2_0.value,
        "threshold": threshold,
        "inputs": None,
    }
    # model was train with product having a name
    if not product.get("product_name"):
        return [], debug
    # ingredients are not mandatory, just insure correct type
    product.setdefault("ingredients_tags", [])
    inputs = {
        "ingredient": product["ingredients_tags"],
        "product_name": [product["product_name"]],
    }
    debug["inputs"] = inputs

    data = {
        "signature_name": "serving_default",
        "instances": [inputs],
    }

    r = http_session.post(
        f"{settings.TF_SERVING_BASE_URL}/category-classifier:predict",
        json=data,
        timeout=(3.0, 10.0),
    )
    r.raise_for_status()
    response = r.json()

    # Since we only sent one product in the query, we can be guaranteed that only one
    # prediction is returned by TF Serving.
    prediction = response["predictions"][0]

    # The response is always in the form:
    #   "predictions": [
    #     {
    #         "output_mapper_layer": [0.868871808, 0.801418602, ...],
    #         "output_mapper_layer_1": ["en:seafood", "en:fishes", ....],
    #     }
    #   ]
    #
    # where 'output_mapper_layer' is the confidence score for a prediction in descending order.
    #       'output_mapper_layer_1' is the category for the prediction score above.
    #
    # The model only returns top 50 predictions.

    category_predictions: list[tuple[str, float]] = []

    # We only consider predictions with a confidence score of `threshold` and above.
    for idx, confidence in enumerate(prediction["output_mapper_layer"]):
        if confidence >= threshold:
            category_predictions.append(
                (
                    prediction["output_mapper_layer_1"][idx],
                    prediction["output_mapper_layer"][idx],
                )
            )
        else:
            break

    return category_predictions, debug
