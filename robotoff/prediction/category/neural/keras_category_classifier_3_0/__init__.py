from typing import Optional

import numpy as np
from tritonclient.grpc import service_pb2

from robotoff.off import generate_image_url, generate_json_ocr_url
from robotoff.prediction.ocr.core import get_ocr_result
from robotoff.triton import (
    deserialize_byte_tensor,
    generate_clip_embedding_request,
    get_triton_inference_stub,
    serialize_byte_tensor,
)
from robotoff.types import JSONType, NeuralCategoryClassifierModel
from robotoff.utils import get_image_from_url, get_logger, http_session

from .preprocessing import (
    IMAGE_EMBEDDING_DIM,
    MAX_IMAGE_EMBEDDING,
    NUTRIMENT_NAMES,
    generate_inputs_dict,
)

logger = get_logger(__name__)


def generate_image_embeddings(product: JSONType, stub) -> Optional[np.ndarray]:
    """Generate image embeddings using CLIP model for the `MAX_IMAGE_EMBEDDING`
    most recent images.

    :param product: product data
    :param stub: the triton inference stub to use
    :return: None if no image was available or a numpy array of shape
        (num_images, IMAGE_EMBEDDING_DIM)
    """
    # Fetch the `MAX_IMAGE_EMBEDDING` most recent "raw" images
    image_ids = sorted(
        (int(image_id) for image_id in product.get("images", {}) if image_id.isdigit()),
        reverse=True,
    )[:MAX_IMAGE_EMBEDDING]
    if image_ids:
        barcode = product["code"]
        image_urls = [
            generate_image_url(barcode, f"{image_id}.400") for image_id in image_ids
        ]
        images = [
            get_image_from_url(image_url, error_raise=False, session=http_session)
            for image_url in image_urls
        ]
        non_null_images = [image for image in images if image is not None]
        if len(images) != len(non_null_images):
            logger.info(
                "%d images could not be fetched (over %d)",
                len(images) - len(non_null_images),
                len(images),
            )

        request = generate_clip_embedding_request(non_null_images)
        response = stub.ModelInfer(request)
        return np.frombuffer(
            response.raw_output_contents[0],
            dtype=np.float32,
        ).reshape((len(non_null_images), -1))
    return None


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
            ocr_texts.append(ocr_result.get_full_text())

    return ocr_texts


def predict(
    product: JSONType,
    ocr_texts: list[str],
    model_name: NeuralCategoryClassifierModel,
    threshold: Optional[float] = None,
    image_embeddings: Optional[np.ndarray] = None,
) -> tuple[list[tuple[str, float]], JSONType]:
    """Predict categories using v3 model.

    :param product: the product for which we want to predict categories
    :param ocr_texts: a list of OCR texts, one string per image
    :param model_name: the name of the model to use
    :param threshold: the detection threshold, default is 0.5
    :param image_embeddings: image embeddings of up to the
        `MAX_IMAGE_EMBEDDING` most recent images or None if no image was
        available
    :return: the predicted categories as a list of
        (category_tag, confidence) tuples and a dict containing debug
        information
    """
    if threshold is None:
        threshold = 0.5

    inputs = generate_inputs_dict(product, ocr_texts, image_embeddings)
    debug = generate_debug_dict(model_name, threshold, inputs)
    scores, labels = _predict(inputs, model_name)
    indices = np.argsort(-scores)

    category_predictions: list[tuple[str, float]] = []

    for idx in indices:
        confidence = float(scores[idx])
        category = labels[idx]
        # We only consider predictions with a confidence score of `threshold` and above.
        if confidence >= threshold:
            category_predictions.append((category, confidence))
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
    inputs: JSONType, model_name: NeuralCategoryClassifierModel
) -> tuple[np.ndarray, list[str]]:
    """Internal method to prepare and run triton request."""
    request = build_triton_request(
        inputs,
        model_name=triton_model_names[model_name],
        **model_input_flags[model_name],
    )
    stub = get_triton_inference_stub()
    response = stub.ModelInfer(request)
    scores = np.frombuffer(response.raw_output_contents[0], dtype=np.float32,).reshape(
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

    if add_product_name:
        product_name_input = service_pb2.ModelInferRequest().InferInputTensor()
        product_name_input.name = "product_name"
        product_name_input.datatype = "BYTES"
        product_name_input.shape.extend([1, 1])
        request.inputs.extend([product_name_input])
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
