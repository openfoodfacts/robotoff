from typing import Dict, List, Optional

from robotoff import settings
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.taxonomy import Taxonomy
from robotoff.utils import http_session


class CategoryPrediction:
    """CategoryPrediction stores information about a category classification prediction."""

    def __init__(self, category: str, confidence: float):
        self.category = category
        self.confidence = confidence

    def to_prediction(self) -> Prediction:
        """Converts this category prediction to a Prediction."""
        return Prediction(
            type=PredictionType.category,
            value_tag=self.category,
            data={"lang": "xx", "model": "neural", "confidence": self.confidence},
        )

    def __eq__(self, other):
        """A CategoryPrediction is equal to another prediction when their attributes match."""
        if not isinstance(other, CategoryPrediction):
            return NotImplemented

        return self.category == other.category and self.confidence == other.confidence


class CategoryClassifier:
    """CategoryClassifier is responsible for generating predictions for a given product."""

    def __init__(self, category_taxonomy: Taxonomy):
        self.taxonomy = category_taxonomy

    def predict(
        self, product: Dict, deepest_only: bool = False
    ) -> Optional[List[CategoryPrediction]]:
        """Returns an unordered list of category predictions for the given product.

        deepest_only: controls whether the returned list should only contain the deepmost categories
        for a predicted taxonomy chain.
        For example, if we predict 'fresh vegetables' -> 'legumes' -> 'beans' for a product,
        setting deepest_only=True will return ['beans']."""

        if "ingredients_tags" not in product or "product_name" not in product:
            return None

        data = {
            "signature_name": "serving_default",
            "instances": [
                {
                    "ingredient": product["ingredients_tags"],
                    "product_name": [product["product_name"]],
                }
            ],
        }

        r = http_session.post(
            f"{settings.TF_SERVING_BASE_URL}/category-classifier:predict", json=data
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

        predictions = []

        # We only consider predictions with a confidence score of 0.5 and above.
        for idx, confidence in enumerate(prediction["output_mapper_layer"]):
            if confidence >= 0.5:
                predictions.append(
                    CategoryPrediction(
                        category=prediction["output_mapper_layer_1"][idx],
                        confidence=prediction["output_mapper_layer"][idx],
                    )
                )
            else:
                break

        if deepest_only:
            predicted_dict = {p.category: p for p in predictions}
            taxonomy_nodes = [self.taxonomy[p.category] for p in predictions]

            predictions = [
                predicted_dict[x.id]
                for x in self.taxonomy.find_deepest_nodes(taxonomy_nodes)
            ]

        if len(predictions) == 0:
            return None
        return predictions
