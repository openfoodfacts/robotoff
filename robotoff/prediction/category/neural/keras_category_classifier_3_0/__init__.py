import functools
from typing import Literal, Optional

import numpy as np
from PIL import Image
from tritonclient.grpc import service_pb2

from robotoff.images import refresh_images_in_db
from robotoff.models import ImageEmbedding, ImageModel, with_db
from robotoff.off import generate_image_url, generate_json_ocr_url
from robotoff.prediction.ocr.core import get_ocr_result
from robotoff.taxonomy import Taxonomy
from robotoff.triton import (
    deserialize_byte_tensor,
    generate_clip_embedding_request,
    serialize_byte_tensor,
)
from robotoff.types import JSONType, NeuralCategoryClassifierModel
from robotoff.utils import get_image_from_url, get_logger, http_session, load_json

from .preprocessing import (
    IMAGE_EMBEDDING_DIM,
    MAX_IMAGE_EMBEDDING,
    NUTRIMENT_NAMES,
    V3_MODEL_DATA_DIR,
    generate_inputs_dict,
)

logger = get_logger(__name__)


# Category IDs to ignore in v3 model predictions
CATEGORY_EXCLUDE_SET = {
    # generic category that was mistakenly forgotten in exclude list
    # in category selection
    "en:meats-and-their-products",
}


def fetch_cached_image_embeddings(
    barcode: str, image_ids: list[str]
) -> dict[str, np.ndarray]:
    """Fetch image embeddings cached in DB for a product and specific image
    IDs.

    Only the embeddings existing in DB are returned, image IDs that were not
    found are ignored.

    :param barcode: the product barcode
    :param image_ids: a list of image IDs to fetch
    :return: a dict mapping image IDs to CLIP image embedding
    """
    cached_embeddings = {}
    for image_id, embedding in (
        ImageEmbedding.select(ImageModel.image_id, ImageEmbedding.embedding)
        .join(ImageModel)
        .where(
            ImageModel.barcode == barcode,
            ImageModel.image_id.in_(image_ids),
        )
        .tuples()
        .iterator()
    ):
        cached_embeddings[image_id] = np.frombuffer(embedding, dtype=np.float32)

    return cached_embeddings


def save_image_embeddings(barcode: str, embeddings: dict[str, np.ndarray]):
    """Save computed image embeddings in ImageEmbedding table.

    :param barcode: barcode of the product
    :param embeddings: a dict mapping image ID to image embedding
    """
    image_id_to_model_id = {
        image_id: model_id
        for (model_id, image_id) in ImageModel.select(
            ImageModel.id, ImageModel.image_id
        )
        .where(
            ImageModel.barcode == barcode,
            ImageModel.image_id.in_(list(embeddings.keys())),
        )
        .tuples()
        .iterator()
    }

    if num_missing_images := sum(
        int(image_id not in image_id_to_model_id) for image_id in embeddings.keys()
    ):
        logger.info("%d images were not found in image table", num_missing_images)

    rows = [
        {"image_id": image_id_to_model_id[image_id], "embedding": embedding.tobytes()}
        for image_id, embedding in embeddings.items()
        if image_id in image_id_to_model_id
    ]
    inserted = ImageEmbedding.insert_many(rows).returning().execute()
    logger.info("%d image embeddings created in db", inserted)


@with_db
def generate_image_embeddings(product: JSONType, stub) -> Optional[np.ndarray]:
    """Generate image embeddings using CLIP model for the `MAX_IMAGE_EMBEDDING`
    most recent images.

    We first fetch image embeddings cached in DB (from ImageEmbedding table),
    and we generate embeddings for missing image IDs by sending a request to
    Triton. We save the computed embeddings in DB (for future usage), and both
    cached and newly-computed embeddings are concatenated and returned.

    :param product: product data
    :param stub: the triton inference stub to use
    :return: None if no image was available or a numpy array of shape
        (num_images, IMAGE_EMBEDDING_DIM)
    """
    # Fetch the `MAX_IMAGE_EMBEDDING` most recent "raw" images
    image_ids_int = sorted(
        # We convert it to int to get a correct recent sorting
        (int(image_id) for image_id in product.get("images", {}) if image_id.isdigit()),
        reverse=True,
    )[:MAX_IMAGE_EMBEDDING]
    # Convert image IDs back to string
    image_ids = [str(image_id) for image_id in image_ids_int]
    if image_ids:
        barcode = product["code"]
        embeddings_by_id = fetch_cached_image_embeddings(barcode, image_ids)
        logger.debug("%d embeddings fetched from DB", len(embeddings_by_id))
        missing_embedding_ids = set(image_ids) - set(embeddings_by_id)

        if missing_embedding_ids:
            logger.debug(
                "Computing embeddings for %d images", len(missing_embedding_ids)
            )
            images_by_id: dict[str, Optional[Image.Image]] = {
                image_id: get_image_from_url(
                    # Images are resized to 224x224, so there is no need to
                    # fetch the full-sized image, the 400px resized
                    # version is enough
                    generate_image_url(barcode, f"{image_id}.400"),
                    error_raise=False,
                    session=http_session,
                )
                for image_id in missing_embedding_ids
            }
            # image may be None if the image does not exist on the server
            # or in case of network error, filter these images
            non_null_image_by_ids = {
                image_id: image
                for image_id, image in images_by_id.items()
                if image is not None
            }
            if len(missing_embedding_ids) != len(non_null_image_by_ids):
                logger.info(
                    "%d images could not be fetched (over %d)",
                    len(missing_embedding_ids) - len(non_null_image_by_ids),
                    len(missing_embedding_ids),
                )

            if non_null_image_by_ids:
                computed_embeddings_by_id = _generate_image_embeddings(
                    non_null_image_by_ids, stub
                )
                # Make sure all image IDs are in image table
                refresh_images_in_db(barcode, product.get("images", {}))
                # Save embeddings in embeddings.image_embeddings table for future
                # use
                save_image_embeddings(barcode, computed_embeddings_by_id)
                # Merge cached and newly-computed image embeddings
                embeddings_by_id |= computed_embeddings_by_id

        if embeddings_by_id:
            # We need at least one array to stack
            return np.stack(list(embeddings_by_id.values()), axis=0)

    return None


def _generate_image_embeddings(
    images_by_id: dict[str, Image.Image], stub
) -> dict[str, np.ndarray]:
    """Generate CLIP image embeddings by sending a request to Triton.

    :param images_by_id: a dict mapping image ID to PIL Image
    :param stub: the triton inference stub to use
    :return: a dict mapping image ID to CLIP embedding
    """
    request = generate_clip_embedding_request(list(images_by_id.values()))
    response = stub.ModelInfer(request)
    computed_embeddings = np.frombuffer(
        response.raw_output_contents[0],
        dtype=np.float32,
    ).reshape((len(images_by_id), -1))
    return {
        image_id: embedding
        for image_id, embedding in zip(images_by_id.keys(), computed_embeddings)
    }


def fetch_ocr_texts(product: JSONType) -> list[str]:
    """Fetch all image OCRs from Product Opener and return a list of the
    detected texts, one string per image."""
    barcode = product.get("code")
    if not barcode:
        return []

    ocr_texts = []
    image_ids = (id_ for id_ in product.get("images", {}).keys() if id_.isdigit())
    for image_id in image_ids:
        ocr_url = generate_json_ocr_url(barcode, image_id)
        ocr_result = get_ocr_result(ocr_url, http_session, error_raise=False)
        if ocr_result:
            ocr_texts.append(ocr_result.get_full_text_contiguous())

    return ocr_texts


@functools.cache
def get_automatic_processing_thresholds() -> dict[str, float]:
    """Return a dict mapping category ID to minimum detection threshold
    required to be able to process the insight automatically.
    Only available for the current default model,
    `keras_image_embeddings_3_0`.

    The threshold was selected category-wise as the lowest threshold for which
    we have a precision >= 0.99 on validation + test dataset for this
    category.
    """
    return load_json(V3_MODEL_DATA_DIR / "image_embeddings_model_thresholds.json.gz", compressed=True)  # type: ignore


# In NeighborPredictionType objects, we stores the score of parents, children
# and sibling categories (relative to the predicted categories). Under each type
# (siblings, children, parents), we store scores as a dict mapping the category
# name to either the score (float) or None if the neighbor category is not part
# of the predicted category list.
NeighborPredictionType = Optional[
    dict[Literal["siblings", "children", "parents"], dict[str, Optional[float]]]
]


def predict(
    product: JSONType,
    ocr_texts: list[str],
    model_name: NeuralCategoryClassifierModel,
    stub,
    threshold: Optional[float] = None,
    image_embeddings: Optional[np.ndarray] = None,
    category_taxonomy: Optional[Taxonomy] = None,
) -> tuple[list[tuple[str, float, Optional[NeighborPredictionType]]], JSONType]:
    """Predict categories using v3 model.

    :param product: the product for which we want to predict categories
    :param ocr_texts: a list of OCR texts, one string per image
    :param model_name: the name of the model to use
    :param stub: the triton inference stub to use
    :param threshold: the detection threshold, default is 0.5
    :param image_embeddings: image embeddings of up to the
        `MAX_IMAGE_EMBEDDING` most recent images or None if no image was
        available
    :param category_taxonomy: the category Taxonomy (optional), if provided
        the predicted scores of parents, children and siblings will be returned
    :return: the predicted categories as a list of
        (category_tag, neighbor_predictions, confidence) tuples and a dict
        containing debug information. `neighbor_predictions` is None if
        taxonomy was not passed, otherwise it's a dict containing predicted
        scores of parents, children and siblings
    """
    if threshold is None:
        threshold = 0.5

    inputs = generate_inputs_dict(product, ocr_texts, image_embeddings)
    debug = generate_debug_dict(model_name, threshold, inputs)
    scores, labels = _predict(inputs, model_name, stub)
    indices = np.argsort(-scores)

    category_predictions: list[tuple[str, float, Optional[NeighborPredictionType]]] = []
    label_to_idx = {label: idx for idx, label in enumerate(labels)}

    for idx in indices:
        confidence = float(scores[idx])
        category = labels[idx]

        if category in CATEGORY_EXCLUDE_SET:
            continue

        # We only consider predictions with a confidence score of `threshold` and above.
        if confidence >= threshold:
            neighbor_predictions: NeighborPredictionType
            if category_taxonomy is not None and category in category_taxonomy:
                neighbor_predictions = {"parents": {}, "children": {}, "siblings": {}}
                current_node = category_taxonomy[category]
                for parent in current_node.parents:
                    neighbor_predictions["parents"][parent.id] = (
                        float(scores[label_to_idx[parent.id]])
                        if parent.id in label_to_idx
                        else None
                    )

                    for sibling in (
                        node for node in parent.children if node != current_node
                    ):
                        neighbor_predictions["siblings"][sibling.id] = (
                            float(scores[label_to_idx[sibling.id]])
                            if sibling.id in label_to_idx
                            else None
                        )

                for child in current_node.children:
                    neighbor_predictions["children"][child.id] = (
                        float(scores[label_to_idx[child.id]])
                        if child.id in label_to_idx
                        else None
                    )
            else:
                neighbor_predictions = None
            category_predictions.append((category, confidence, neighbor_predictions))
        else:
            break

    return category_predictions, debug


def generate_debug_dict(
    model_name: NeuralCategoryClassifierModel, threshold: float, inputs: JSONType
) -> JSONType:
    """Generate dict containing debug information.

    :param model_name: name of the model used during prediction
    :param threshold: detection threshold used
    :param inputs: inputs dict used for inference
    :return: the debug dict
    """
    debug = {
        "model_name": model_name.value,
        "threshold": threshold,
        "inputs": {
            k: v
            for k, v in inputs.items()
            # Don't keep numpy ndarray in debug.inputs dict
            if k not in ("image_embeddings", "image_embeddings_mask")
        },
    }

    if inputs["image_embeddings_mask"].sum() == 1:
        # `image_embeddings_mask` always has at least one non-zero element,
        # check whether there is an image or not by checking if
        # `image_embeddings` is zero-filled
        num_images = 0 if np.all(inputs["image_embeddings"][0] == 0) else 1
    else:
        num_images = int(inputs["image_embeddings_mask"].sum())

    debug["inputs"]["num_images"] = num_images  # type: ignore
    return debug


# Parameters on how to prepare data for each model type, see `build_triton_request`
model_input_flags: dict[NeuralCategoryClassifierModel, dict] = {
    NeuralCategoryClassifierModel.keras_image_embeddings_3_0: {},
    NeuralCategoryClassifierModel.keras_300_epochs_3_0: {"add_image_embeddings": False},
    NeuralCategoryClassifierModel.keras_ingredient_ocr_3_0: {
        "add_image_embeddings": False,
    },
    NeuralCategoryClassifierModel.keras_baseline_3_0: {
        "add_ingredients_ocr_tags": False,
        "add_image_embeddings": False,
    },
    NeuralCategoryClassifierModel.keras_original_3_0: {
        "add_ingredients_ocr_tags": False,
        "add_nutriments": False,
        "add_image_embeddings": False,
    },
    NeuralCategoryClassifierModel.keras_product_name_only_3_0: {
        "add_ingredients_ocr_tags": False,
        "add_nutriments": False,
        "add_ingredient_tags": False,
        "add_image_embeddings": False,
    },
}

triton_model_names = {
    NeuralCategoryClassifierModel.keras_image_embeddings_3_0: "category-classifier-keras-image-embeddings-3.0",
    NeuralCategoryClassifierModel.keras_300_epochs_3_0: "category-classifier-keras-300-epochs-3.0",
    NeuralCategoryClassifierModel.keras_ingredient_ocr_3_0: "category-classifier-keras-ingredient-ocr-3.0",
    NeuralCategoryClassifierModel.keras_baseline_3_0: "category-classifier-keras-baseline-3.0",
    NeuralCategoryClassifierModel.keras_original_3_0: "category-classifier-keras-original-3.0",
    NeuralCategoryClassifierModel.keras_product_name_only_3_0: "category-classifier-keras-product-name-only-3.0",
}


def _predict(
    inputs: JSONType, model_name: NeuralCategoryClassifierModel, stub
) -> tuple[np.ndarray, list[str]]:
    """Internal method to prepare and run triton request."""
    request = build_triton_request(
        inputs,
        model_name=triton_model_names[model_name],
        **model_input_flags[model_name],
    )
    response = stub.ModelInfer(request)
    scores = np.frombuffer(response.raw_output_contents[0], dtype=np.float32).reshape(
        (1, -1)
    )[0]
    labels = deserialize_byte_tensor(response.raw_output_contents[1])
    return scores, labels


def build_triton_request(
    inputs: JSONType,
    model_name: str,
    add_product_name: bool = True,
    add_ingredient_tags: bool = True,
    add_nutriments: bool = True,
    add_ingredients_ocr_tags: bool = True,
    add_image_embeddings: bool = True,
):
    """Build a Triton ModelInferRequest gRPC request.

    :param inputs: the input dict, as generated by
        `generate_inputs_dict`
    :param model_name: the name of the model to use, see global variable
        `triton_model_names` for possible values
    :param add_product_name: if True, add product name as input, defaults to
        True
    :param add_ingredient_tags: if True, add ingredients as input, defaults
        to True
    :param add_nutriments: if True, add all nutriments as input, defaults to
        True
    :param add_ingredients_ocr_tags: if True, add ingredients extracted from
        OCR as input, defaults to True
    :param add_image_embeddings: if True, add image embeddings as input,
        defaults to True
    :return: the gRPC ModelInferRequest
    """
    product_name = inputs["product_name"]
    ingredients_tags = inputs["ingredients_tags"]
    ingredients_ocr_tags = inputs["ingredients_ocr_tags"]
    request = service_pb2.ModelInferRequest()
    request.model_name = model_name

    # for each input, we must specify the input name, the data type, the shape
    # and the raw data as a byte-serialized numpy array
    if add_product_name:
        product_name_input = service_pb2.ModelInferRequest().InferInputTensor()
        product_name_input.name = "product_name"
        # String must be provided as bytes
        product_name_input.datatype = "BYTES"
        # First dimension is batch size
        product_name_input.shape.extend([1, 1])
        # We must use extend method with protobuf to add an item to a list
        request.inputs.extend([product_name_input])
        # String must be provided as byte-serialized object numpy arrays
        request.raw_input_contents.extend(
            [serialize_byte_tensor(np.array([[product_name]], dtype=object))]
        )

    if add_ingredient_tags:
        ingredients_tags_input = service_pb2.ModelInferRequest().InferInputTensor()
        ingredients_tags_input.name = "ingredients_tags"
        ingredients_tags_input.datatype = "BYTES"
        ingredients_tags_input.shape.extend([1, len(ingredients_tags)])
        request.inputs.extend([ingredients_tags_input])
        request.raw_input_contents.extend(
            [serialize_byte_tensor(np.array([ingredients_tags], dtype=object))]
        )

    if add_nutriments:
        for nutriment_name in NUTRIMENT_NAMES:
            nutriment_input = service_pb2.ModelInferRequest().InferInputTensor()
            nutriment_input.name = nutriment_name
            nutriment_input.datatype = "FP32"
            nutriment_input.shape.extend([1, 1])
            request.inputs.extend([nutriment_input])
            value = inputs[nutriment_name]
            request.raw_input_contents.extend(
                [np.array([[value]], dtype=np.float32).tobytes()]
            )

    if add_ingredients_ocr_tags:
        ingredients_ocr_tags_input = service_pb2.ModelInferRequest().InferInputTensor()
        ingredients_ocr_tags_input.name = "ingredients_ocr_tags"
        ingredients_ocr_tags_input.datatype = "BYTES"
        ingredients_ocr_tags_input.shape.extend([1, len(ingredients_ocr_tags)])
        request.inputs.extend([ingredients_ocr_tags_input])
        request.raw_input_contents.extend(
            [serialize_byte_tensor(np.array([ingredients_ocr_tags], dtype=object))]
        )

    if add_image_embeddings:
        image_embeddings_input = service_pb2.ModelInferRequest().InferInputTensor()
        image_embeddings_input.name = "image_embeddings"
        image_embeddings_input.datatype = "FP32"
        image_embeddings_input.shape.extend(
            [1, MAX_IMAGE_EMBEDDING, IMAGE_EMBEDDING_DIM]
        )
        request.inputs.extend([image_embeddings_input])
        value = inputs["image_embeddings"]
        request.raw_input_contents.extend([value.tobytes()])

        image_embeddings_mask_input = service_pb2.ModelInferRequest().InferInputTensor()
        image_embeddings_mask_input.name = "image_embeddings_mask"
        image_embeddings_mask_input.datatype = "FP32"
        image_embeddings_mask_input.shape.extend([1, MAX_IMAGE_EMBEDDING])
        request.inputs.extend([image_embeddings_mask_input])
        value = inputs["image_embeddings_mask"]
        request.raw_input_contents.extend([value.tobytes()])

    return request
