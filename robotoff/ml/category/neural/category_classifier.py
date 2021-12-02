from typing import Dict, List, Optional

from robotoff import settings
from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import RawInsight
from robotoff.utils import get_logger, http_session

logger = get_logger()


class Prediction:
    """Prediction stores information about a category classification prediction."""

    def __init__(self, category: str, confidence: float):
        self.category = category
        self.confidence = confidence

    def to_raw_insight(self) -> RawInsight:
        """Converts this prediction to a RawInsight."""
        return RawInsight(
            type=InsightType.category,
            value_tag=self.category,
            data={
                "lang": "xx",
                "model": "neural",
                "confidence": self.confidence,
            },
        )


class CategoryClassifier:
    """CategoryClassifier is responsible for generating predictions for a given product."""

    def predict(
        self, product: Dict, deepest_only: bool = False
    ) -> Optional[List[Prediction]]:
        """Returns an unordered list of category predictions for the given product.

        deepest_only: controls whether the returned list should only contain the deepmost categories
        for a predicted taxonomy chain.
        For example, if we predict 'fresh vegetables' -> 'legumes' -> 'beans' for a product,
        setting deepest_only=True will return ['beans']."""
        data = {
            "signature_name": "serving_default",
            "instances": [
                {
                    "ingredient": product["known_ingredient_tags"],
                    "product_name": [product["product_name"]],
                }
            ],
        }

        r = http_session.post(
            f"{settings.TF_SERVING_BASE_URL}/category-classifier:predict", json=data
        )
        r.raise_for_status()  # TODO(kulizhsy): handle this on the caller side?
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

        predictions = []

        # We only consider predictions with a confidence score of 0.5 and above.
        for idx, confidence in enumerate(prediction["output_mapper_layer"]):
            if confidence >= 0.5:
                predictions.append(
                    Prediction(
                        category=prediction["output_mapper_layer_1"][idx],
                        confidence=prediction["output_mapper_layer"][idx],
                    )
                )
            else:
                break

        # TODO(kulizhsy): support deepest_only &(figure out why we want to use it as opposed to all predictions.)

        # if deepest_only:
        #     category_to_confidence = dict(product_predicted)
        #     product_predicted = [
        #         (x.id, category_to_confidence[x.id])
        #         for x in taxonomy.find_deepest_nodes(
        #             [taxonomy[c] for c, confidence in product_predicted]
        #         )
        #     ]
        # predicted.append(product_predicted)

        if len(predictions) == 0:
            return None
        return predictions
