import logging
from typing import Any

import numpy as np

from robotoff import settings
from robotoff.taxonomy import Taxonomy
from robotoff.triton import get_triton_inference_stub
from robotoff.types import (
    JSONType,
    NeuralCategoryClassifierModel,
    Prediction,
    PredictionType,
    ProductIdentifier,
)

from . import keras_category_classifier_3_0

logger = logging.getLogger(__name__)


def create_prediction(
    category: str,
    confidence: float,
    model_version: str,
    product_id: ProductIdentifier,
    **kwargs,
) -> Prediction:
    """Create a Prediction.

    kwargs are added to the prediction data field.

    :param category: canonical ID of the category, ex: en:cheeses
    :param confidence: confidence score of the model, between 0.0 and 1.0
    :param model_version: version of the model, see
        NeuralCategoryClassifierModel values for possible values.
        ex: `keras-image-embeddings-3.0`
    :param product_id: identifier of the product
    """
    return Prediction(
        type=PredictionType.category,
        value_tag=category,
        data=kwargs,
        automatic_processing=False,
        predictor="neural",
        predictor_version=model_version,
        confidence=confidence,
        barcode=product_id.barcode,
        server_type=product_id.server_type,
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
        product_id: ProductIdentifier,
        deepest_only: bool = False,
        threshold: float | None = None,
        model_name: NeuralCategoryClassifierModel | None = None,
        clear_cache: bool = False,
        triton_uri: str | None = None,
    ) -> tuple[list[Prediction], JSONType]:
        """Return an unordered list of category predictions for the given
        product and additional debug information.

        :param product: the product to predict the categories from, the
            following fields are used as input:
            - `product_name`: the product name in the main language of the
              product
            - `ingredients`: a list of ingredient tags (ex: ["en:chicken"])
            - `nutriments`: a dict with mapping nutriment name to value for
              100g of product. The following nutriment names are accepted:
              `fat_100g`, `saturated-fat_100g`, `carbohydrates_100g`,
              `sugars_100g`, `fiber_100g`, `proteins_100g`, `salt_100g`,
              `energy-kcal_100g`, `fruits-vegetables-nuts_100g`.
              Don't provide the nutriment if the value is missing.
            - `ocr`: a list of string corresponding to the text extracted from
              the product images with OCR. Each element of the list is the
              text of a single image, the list order doesn't affect
              predictions. We use OCR text to detect ingredient mentions and
              use it as a model input.
              For optimal results, this field should be provided even if
              `ingredients` is provided.
              This fields is optional. If `ocr` is not provided, we fetch OCR
              texts from Product Opener using  `product.code` and
              `product.images` fields to build OCR URLs.
            - `image_embeddings`: embeddings of the 10 most recent product
              images generated with clip-vit-base-patch32 model.
              Each item of the list is the embedding of a single image,
              provided as a list of dimension 512. Shape: (num_images, 512).
              This field is optional. If `image_embeddings` is not provided,
              we fetch the 10 most recent images from Product Opener using
              `product.code` and `product.images` fields to build image URLs.
              We then compute image embeddings and cache them in
              `embeddings.image_embedding` DB table. These cached embeddings
              will be used instead of computing embeddings from scratch for
              subsequent calls.
            - `code` and `images`: these fields are only used if `ocr` or
              `image_embeddings` are not provided, to generate OCR texts and
              image embeddings respectively.
        :param product_id: identifier of the product
        :param deepest_only: controls whether the returned list should only
            contain the deepmost categories for a predicted taxonomy chain.

            For example, if we predict 'fresh vegetables' -> 'legumes' ->
            'beans' for a product,
            setting deepest_only=True will return ['beans'].
        :param threshold: the score above which we consider the category to be
            detected (default: 0.5)
        :param neural_model_name: the name of the neural model to use to
            perform prediction. `keras_image_embeddings_3_0` is used by
            default.
        :param clear_cache: if True, clear ingredient processing cache before
            returning results
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
            Note that we use different default URIs for different models,
            so you should set this parameter only if you want to use a custom
            Triton Inference Server URI for all models.
        """
        if threshold is None:
            threshold = 0.5

        if model_name is None:
            model_name = NeuralCategoryClassifierModel.keras_image_embeddings_3_0

        logger.debug("predicting category with model %s", model_name)

        if "ocr" in product:
            # We check that the OCR text list was not provided manually in
            # `product` dict
            ocr_texts = product.pop("ocr")
        else:
            # Otherwise we fetch OCR texts from Product Opener
            ocr_texts = keras_category_classifier_3_0.fetch_ocr_texts(
                product, product_id
            )

        # We check whether image embeddings were provided as input
        if "image_embeddings" in product:
            if product["image_embeddings"]:
                image_embeddings = np.array(
                    product["image_embeddings"], dtype=np.float32
                )

                if image_embeddings.ndim != 2 or image_embeddings.shape[1] != 512:
                    raise ValueError(
                        "invalid shape for image embeddings: %s, expected (-1, 512)",
                        image_embeddings.shape,
                    )
            else:
                # No image available
                image_embeddings = None
        else:
            # Or we generate them (or fetch them from DB cache)
            triton_stub_clip = get_triton_inference_stub(
                triton_uri or settings.TRITON_URI_CLIP
            )
            image_embeddings = keras_category_classifier_3_0.generate_image_embeddings(
                product, product_id, triton_stub_clip
            )

        triton_stub = get_triton_inference_stub(
            triton_uri or settings.TRITON_URI_CATEGORY_CLASSIFIER
        )
        raw_predictions, debug = keras_category_classifier_3_0.predict(
            product,
            ocr_texts,
            model_name,
            stub=triton_stub,
            threshold=threshold,
            image_embeddings=image_embeddings,
            category_taxonomy=self.taxonomy,
            clear_cache=clear_cache,
        )
        predictions = []

        for category_id, score, neighbor_predictions in raw_predictions:
            if category_id not in self.taxonomy:
                # If the category no longer exist in the taxonomy, ignore it
                continue
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
                    product_id=product_id,
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
