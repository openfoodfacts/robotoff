from typing import Any, Optional

from robotoff.taxonomy import Taxonomy
from robotoff.triton import get_triton_inference_stub
from robotoff.types import (
    JSONType,
    NeuralCategoryClassifierModel,
    Prediction,
    PredictionType,
)
from robotoff.utils import get_logger

from . import keras_category_classifier_2_0, keras_category_classifier_3_0

logger = get_logger(__name__)


def create_prediction(
    category: str, confidence: float, model_version: str, **kwargs
) -> Prediction:
    """Create a Prediction.

    kwargs are added to the prediction data field.

    :param category: canonical ID of the category, ex: en:cheeses
    :param confidence: confidence score of the model, between 0.0 and 1.0
    :param model_version: version of the model, see
        NeuralCategoryClassifierModel values for possible values.
        ex: `keras-image-embeddings-3.0`
    """
    return Prediction(
        type=PredictionType.category,
        value_tag=category,
        data={"model_version": model_version, **kwargs},
        automatic_processing=False,
        predictor="neural",
        confidence=confidence,
    )


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
            prediction. `keras_image_embeddings_3_0` is used by default.
        """
        logger.debug("predicting category with model %s", model_name)

        if threshold is None:
            threshold = 0.5

        if model_name is None:
            model_name = NeuralCategoryClassifierModel.keras_image_embeddings_3_0

        if model_name == NeuralCategoryClassifierModel.keras_2_0:
            raw_v2_predictions, debug = keras_category_classifier_2_0.predict(
                product, threshold
            )
            # v3 models have an additional field for neighbor predictions, change
            # the `raw_predictions` format to be compatible with v3 models
            raw_predictions: list[
                tuple[
                    str,
                    float,
                    Optional[keras_category_classifier_3_0.NeighborPredictionType],
                ]
            ] = [
                (category_id, score, None) for category_id, score in raw_v2_predictions
            ]
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
                # Only fetch OCR texts if it's required by the model
                ocr_texts = (
                    keras_category_classifier_3_0.fetch_ocr_texts(product)
                    if keras_category_classifier_3_0.model_input_flags[model_name].get(
                        "add_ingredients_ocr_tags", True
                    )
                    else []
                )

            # Only generate image embeddings if it's required by the model
            triton_stub = get_triton_inference_stub()
            image_embeddings = (
                keras_category_classifier_3_0.generate_image_embeddings(
                    product, triton_stub
                )
                if keras_category_classifier_3_0.model_input_flags[model_name].get(
                    "add_image_embeddings", True
                )
                else None
            )
            raw_predictions, debug = keras_category_classifier_3_0.predict(
                product,
                ocr_texts,
                model_name,
                stub=triton_stub,
                threshold=threshold,
                image_embeddings=image_embeddings,
                category_taxonomy=self.taxonomy,
            )

        # Threshold for automatic detection, only available for
        # `keras_image_embeddings_3_0` model.
        # Currently we don't apply yet the category automatically, we only add
        # a flag to add a specific annotation campaign during the insight
        # import
        thresholds = (
            (keras_category_classifier_3_0.get_automatic_processing_thresholds())
            if model_name.keras_image_embeddings_3_0
            else {}
        )

        predictions = []

        for category_id, score, neighbor_predictions in raw_predictions:
            if category_id not in self.taxonomy:
                # If the category no longer exist in the taxonomy, ignore it
                continue
            # If the category is not in `thresholds` or if the score is
            # below the threshold, set the above_threshold flag to False
            above_threshold = score >= thresholds.get(category_id, 1.1)
            kwargs: dict[str, Any] = (
                {}
                if neighbor_predictions is None
                else {"neighbor_predictions": neighbor_predictions}
            )
            predictions.append(
                create_prediction(
                    category_id,
                    score,
                    model_name.value,
                    above_threshold=above_threshold,
                    # We need to set a higher priority (=lower digit) if
                    # above_threshold is True, as otherwise a deepest
                    # predicted category with `above_threshold=False` will
                    # take precedence, and we wouldn't generate any insight
                    # for the prediction with `above_threshold=True`
                    priority=0 if above_threshold else 1,
                    **kwargs,
                )
            )

        if deepest_only:
            predicted_dict = {p.value_tag: p for p in predictions}
            taxonomy_nodes = [self.taxonomy[p.value_tag] for p in predictions]  # type: ignore

            predictions = [
                predicted_dict[x.id]
                for x in self.taxonomy.find_deepest_nodes(taxonomy_nodes)
            ]

        return predictions, debug
