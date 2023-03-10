from typing import Optional

from robotoff.prediction.types import Prediction
from robotoff.taxonomy import Taxonomy
from robotoff.triton import get_triton_inference_stub
from robotoff.types import JSONType, NeuralCategoryClassifierModel, PredictionType
from robotoff.utils import get_logger

from . import keras_category_classifier_2_0, keras_category_classifier_3_0

logger = get_logger(__name__)


class CategoryPrediction:
    """CategoryPrediction stores information about a category classification prediction."""

    def __init__(self, category: str, confidence: float, model_version: str):
        self.category = category
        self.confidence = confidence
        self.model_version = model_version

    def to_prediction(self) -> Prediction:
        """Converts this category prediction to a Prediction."""
        return Prediction(
            type=PredictionType.category,
            value_tag=self.category,
            data={"model_version": self.model_version},
            automatic_processing=False,
            predictor="neural",
            confidence=self.confidence,
        )

    def __eq__(self, other):
        """A CategoryPrediction is equal to another prediction when their attributes match."""
        if not isinstance(other, CategoryPrediction):
            return NotImplemented

        return self.category == other.category and self.confidence == other.confidence


class CategoryClassifier:
    """CategoryClassifier is responsible for generating predictions for a
    given product.

    param category_taxonomy: the Taxonomy.
        This is used to have hierarchy in order to remove parents from
        resulting category set.
    """

    def __init__(self, category_taxonomy: Taxonomy):
        self.taxonomy = category_taxonomy

    def predict(
        self,
        product: dict,
        deepest_only: bool = False,
        threshold: Optional[float] = None,
        model_name: Optional[NeuralCategoryClassifierModel] = None,
    ) -> tuple[list[Prediction], JSONType]:
        """Return an unordered list of category predictions for the given
        product and additional debug information.

        :param product: the product to predict the categories from, should
            have at least `product_name` and `ingredients_tags` fields
        :param deepest_only: controls whether the returned list should only
            contain the deepmost categories for a predicted taxonomy chain.

            For example, if we predict 'fresh vegetables' -> 'legumes' ->
            'beans' for a product,
            setting deepest_only=True will return ['beans'].
        :param threshold: the score above which we consider the category to be
            detected (default: 0.5)
        :param neural_model_name: the name of the neural model to use to perform
            prediction. `keras_2_0` is used by default.
        """
        logger.debug("predicting category with model %s", model_name)

        if threshold is None:
            threshold = 0.5

        if model_name is None:
            model_name = NeuralCategoryClassifierModel.keras_2_0

        if model_name == NeuralCategoryClassifierModel.keras_2_0:
            raw_predictions, debug = keras_category_classifier_2_0.predict(
                product, threshold
            )
        else:
            if "ingredients_tags" in product and "ingredients" not in product:
                # v3 models use the `ingredients` field instead of `ingredients_tags`,
                # so that we only consider ingredients of depth 0.
                # To keep a single interface between v2 and v3 models in Robotoff
                # /predict/category route, we generate the `ingredients` field
                # from `ingredients` tags if it is missing
                product["ingredients"] = [
                    {"id": id_} for id_ in product["ingredients_tags"]
                ]

            if "ocr" in product:
                # We check that the OCR text list was not provided manually in `product`
                # dict
                ocr_texts = product.pop("ocr")
            else:
                # Otherwise we fetch OCR texts from Product Opener
                ocr_texts = keras_category_classifier_3_0.fetch_ocr_texts(product)

            triton_stub = get_triton_inference_stub()
            image_embeddings = keras_category_classifier_3_0.generate_image_embeddings(
                product, triton_stub
            )
            raw_predictions, debug = keras_category_classifier_3_0.predict(
                product,
                ocr_texts,
                model_name,
                threshold=threshold,
                image_embeddings=image_embeddings,
            )

        category_predictions = [
            CategoryPrediction(*item, model_name.value) for item in raw_predictions
        ]

        if deepest_only:
            predicted_dict = {p.category: p for p in category_predictions}
            taxonomy_nodes = [self.taxonomy[p.category] for p in category_predictions]

            category_predictions = [
                predicted_dict[x.id]
                for x in self.taxonomy.find_deepest_nodes(taxonomy_nodes)
            ]

        predictions = [
            category_prediction.to_prediction()
            for category_prediction in category_predictions
        ]
        return predictions, debug
