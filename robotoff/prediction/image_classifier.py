import math
import time
import typing
from typing import Callable

import albumentations as A
import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from tritonclient.grpc import service_pb2

from robotoff.triton import get_triton_inference_stub
from robotoff.types import ImageClassificationModel
from robotoff.utils import get_logger

logger = get_logger(__name__)


class ModelConfig(BaseModel):
    """Configuration of an image classification model."""

    model_name: str = Field(
        ...,
        description="The name of the model, it will be used as "
        "`model_name` field in `image_prediction` table",
    )
    model_version: str = Field(
        ...,
        description="The version of the model, it will be used as "
        "`model_version` field in `image_prediction` table",
    )
    triton_version: str = Field(
        ...,
        description="The version of the model used on Triton Inference Server (eg: `1`)",
    )
    triton_model_name: str = Field(
        ..., description="The name of the model on Triton Inference Server"
    )
    image_size: int = Field(
        ...,
        description="The size of the image expected by the model. "
        "The original image will be resized to this size.",
    )
    label_names: list[str] = Field(
        ...,
        description="The names of the labels used by the model. "
        "The order of the labels must match the order of the classes in the model.",
    )
    transform_func: Callable = Field(
        ...,
        description="A callable function that applies the necessary transformations "
        "to the input image before passing it to the model. ",
    )
    transform_func_expects_numpy: bool = Field(
        default=True,
        description="Whether the `transform_func` expects a NumPy array as input. "
        "If False, it will expect a Pillow image.",
    )


DEFAULT_MEAN = (0.0, 0.0, 0.0)
DEFAULT_STD = (1.0, 1.0, 1.0)


def classify_transforms_pad(max_size: int):
    return A.Compose(
        [
            A.LongestMaxSize(max_size=max_size, p=1.0),
            A.PadIfNeeded(min_height=max_size, min_width=max_size, p=1.0),
            A.Normalize(mean=DEFAULT_MEAN, std=DEFAULT_STD, p=1.0),
        ]
    )


def classify_transforms_crop_center_albumentations(max_size: int):
    return A.Compose(
        [
            A.SmallestMaxSize(max_size=max_size, p=1.0),
            A.CenterCrop(height=max_size, width=max_size, p=1.0),
            A.Normalize(mean=DEFAULT_MEAN, std=DEFAULT_STD, p=1.0),
        ]
    )


def classify_transforms_crop_center(
    max_size: int = 224,
    mean=DEFAULT_MEAN,
    std=DEFAULT_STD,
    interpolation=Image.Resampling.BILINEAR,
    crop_fraction: float = 1.0,
) -> Callable:
    """
    Applies a series of image transformations including resizing, center cropping,
    normalization, and conversion to a NumPy array.

    Transformation steps is based on the one used in the Ultralytics library:
    https://github.com/ultralytics/ultralytics/blob/main/ultralytics/data/augment.py#L2319

    :param img: Input Pillow image.
    :param size: The target size for the transformed image (shortest edge).
    :param mean: Mean values for each RGB channel used in normalization.
    :param std: Standard deviation values for each RGB channel used in normalization.
    :param interpolation: Interpolation method from PIL (Image.Resampling.NEAREST,
        Image.Resampling.BILINEAR, Image.Resampling.BICUBIC).
    :param crop_fraction: Fraction of the image to be cropped.
    :return: The transformed image as a NumPy array.
    """

    def transform(image: Image.Image) -> dict[str, np.ndarray]:
        # Step 1: Resize while preserving the aspect ratio
        width, height = image.size

        # Calculate scale size while preserving aspect ratio
        scale_size = math.floor(max_size / crop_fraction)

        aspect_ratio = width / height
        if width < height:
            new_width = scale_size
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = scale_size
            new_width = int(new_height * aspect_ratio)

        image = image.resize((new_width, new_height), interpolation)

        # Step 2: Center crop
        left = (new_width - max_size) // 2
        top = (new_height - max_size) // 2
        right = left + max_size
        bottom = top + max_size
        image = image.crop((left, top, right, bottom))

        # Step 3: Convert the image to a NumPy array and scale pixel values to [0, 1]
        image_array = np.array(image).astype(np.float32) / 255.0

        # Step 4: Normalize the image
        mean_array = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
        std_array = np.array(std, dtype=np.float32).reshape(1, 1, 3)
        image_array = (image_array - mean_array) / std_array

        return {"image": image_array}

    return transform


MODELS_CONFIG = {
    ImageClassificationModel.price_proof_classification: ModelConfig(
        model_name="price_proof_classification",
        model_version="price_proof_classification_1.0",
        triton_version="1",
        triton_model_name="price_proof_classification",
        image_size=224,
        label_names=[
            "OTHER",
            "PRICE_TAG",
            "PRODUCT_WITH_PRICE",
            "RECEIPT",
            "SHELF",
            "WEB_PRINT",
        ],
        # The price proof classification model was trained with center cropped images
        # It should be trained again as we can expect performance gain with padding
        transform_func=classify_transforms_crop_center(max_size=224),
        transform_func_expects_numpy=False,
    ),
    ImageClassificationModel.front_image_classification: ModelConfig(
        model_name="front_image_classification",
        model_version="front_image_classification_1.0",
        triton_version="1",
        triton_model_name="front_image_classification",
        image_size=448,
        label_names=["FRONT", "OTHER"],
        # the front image classification model was trained with padded images
        # to preserve the aspect ratio
        transform_func=classify_transforms_pad(max_size=448),
    ),
}


class ImageClassifier:
    def __init__(self, config: ModelConfig):
        self.config = config

    def predict(
        self,
        image: Image.Image,
        triton_uri: str | None = None,
    ) -> list[tuple[str, float]]:
        """Run an image classification model on an image.

        The model is expected to have been trained with Ultralytics library (Yolov8).

        :param image: the input Pillow image
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :return: the prediction results as a list of tuples (label, confidence)
        """
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Rotate the image based on the EXIF orientation if needed
        image = typing.cast(Image.Image, ImageOps.exif_transpose(image))

        transform_input = (
            np.array(image) if self.config.transform_func_expects_numpy else image
        )
        image_array = self.config.transform_func(image=transform_input)["image"]
        # Step 5: Change the order of dimensions from (H, W, C) to (C, H, W)
        image_array = np.transpose(image_array, (2, 0, 1))
        image_array = np.expand_dims(image_array, axis=0)

        logger.info(f"Image shape after transformation: {image_array.shape}")
        grpc_stub = get_triton_inference_stub(triton_uri)
        request = service_pb2.ModelInferRequest()
        request.model_name = self.config.triton_model_name

        image_input = service_pb2.ModelInferRequest().InferInputTensor()
        image_input.name = "images"

        image_input.datatype = "FP32"

        image_input.shape.extend([1, 3, self.config.image_size, self.config.image_size])
        request.inputs.extend([image_input])

        output = service_pb2.ModelInferRequest().InferRequestedOutputTensor()
        output.name = "output0"
        request.outputs.extend([output])

        request.raw_input_contents.extend([image_array.tobytes()])
        start_time = time.monotonic()
        response = grpc_stub.ModelInfer(request)
        latency = time.monotonic() - start_time

        logger.debug("Inference time for %s: %s", self.config.model_name, latency)

        start_time = time.monotonic()
        if len(response.outputs) != 1:
            raise Exception(f"expected 1 output, got {len(response.outputs)}")

        if len(response.raw_output_contents) != 1:
            raise Exception(
                f"expected 1 raw output content, got {len(response.raw_output_contents)}"
            )

        output_index = {output.name: i for i, output in enumerate(response.outputs)}
        output = np.frombuffer(
            response.raw_output_contents[output_index["output0"]],
            dtype=np.float32,
        ).reshape((1, len(self.config.label_names)))[0]

        score_indices = np.argsort(-output)

        latency = time.monotonic() - start_time
        logger.debug("Post-processing time for %s: %s", self.config.model_name, latency)
        return [(self.config.label_names[i], float(output[i])) for i in score_indices]
