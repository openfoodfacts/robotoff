from typing import Optional

from robotoff import settings
from robotoff.prediction.types import Prediction
from robotoff.taxonomy import Taxonomy
from robotoff.types import PredictionType
from robotoff.utils import http_session


class CategoryPrediction:
    """CategoryPrediction stores information about a category classification prediction."""

    #: threshold on the neural model confidence to automatically apply prediction
    NEURAL_CONFIDENCE_THRESHOLD = 1.1  # deactivated for now, 1.1 is above 1

    def __init__(self, category: str, confidence: float):
        self.category = category
        self.confidence = confidence

    def to_prediction(self) -> Prediction:
        """Converts this category prediction to a Prediction."""
        return Prediction(
            type=PredictionType.category,
            value_tag=self.category,
            data={"lang": "xx", "confidence": self.confidence},
            automatic_processing=self.confidence >= self.NEURAL_CONFIDENCE_THRESHOLD,
            predictor="neural",
        )

    def __eq__(self, other):
        """A CategoryPrediction is equal to another prediction when their attributes match."""
        if not isinstance(other, CategoryPrediction):
            return NotImplemented

        return self.category == other.category and self.confidence == other.confidence


class CategoryClassifier:
    """CategoryClassifier is responsible for generating predictions for a given product.

    param category_taxonomy: the Taxonomy.
        This is used to have hierarchy in order to remove parents from resulting category set.
    """

    def __init__(self, category_taxonomy: Taxonomy):
        self.taxonomy = category_taxonomy

    def predict(
        self,
        product: dict,
        deepest_only: bool = False,
        threshold: Optional[float] = None,
    ) -> list[Prediction]:
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

        # model was train with product having a name
        if not product.get("product_name"):
            return []
        # ingredients are not mandatory, just insure correct type
        product.setdefault("ingredients_tags", [])

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

        category_predictions: list[CategoryPrediction] = []

        # We only consider predictions with a confidence score of `threshold` and above.
        for idx, confidence in enumerate(prediction["output_mapper_layer"]):
            if confidence >= threshold:
                category_predictions.append(
                    CategoryPrediction(
                        category=prediction["output_mapper_layer_1"][idx],
                        confidence=prediction["output_mapper_layer"][idx],
                    )
                )
            else:
                break

        if deepest_only:
            predicted_dict = {p.category: p for p in category_predictions}
            taxonomy_nodes = [self.taxonomy[p.category] for p in category_predictions]

            category_predictions = [
                predicted_dict[x.id]
                for x in self.taxonomy.find_deepest_nodes(taxonomy_nodes)
            ]

        return [
            category_prediction.to_prediction()
            for category_prediction in category_predictions
        ]
