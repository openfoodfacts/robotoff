import math
import time
import typing

import numpy as np
from PIL import Image, ImageOps
from tritonclient.grpc import service_pb2

from robotoff.triton import get_triton_inference_stub
from robotoff.types import ImageClassificationModel
from robotoff.utils import get_logger

logger = get_logger(__name__)


LABEL_NAMES = {
    ImageClassificationModel.price_proof_classification: [
        "OTHER",
        "PRICE_TAG",
        "PRODUCT_WITH_PRICE",
        "RECEIPT",
        "SHELF",
        "WEB_PRINT",
    ]
}


def classify_transforms(
    img: Image.Image,
    size: int = 224,
    mean=(0.0, 0.0, 0.0),
    std=(1.0, 1.0, 1.0),
    interpolation=Image.Resampling.BILINEAR,
    crop_fraction: float = 1.0,
) -> np.ndarray:
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
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Rotate the image based on the EXIF orientation if needed
    img = typing.cast(Image.Image, ImageOps.exif_transpose(img))

    # Step 1: Resize while preserving the aspect ratio
    width, height = img.size

    # Calculate scale size while preserving aspect ratio
    scale_size = math.floor(size / crop_fraction)

    aspect_ratio = width / height
    if width < height:
        new_width = scale_size
        new_height = int(new_width / aspect_ratio)
    else:
        new_height = scale_size
        new_width = int(new_height * aspect_ratio)

    img = img.resize((new_width, new_height), interpolation)

    # Step 2: Center crop
    left = (new_width - size) // 2
    top = (new_height - size) // 2
    right = left + size
    bottom = top + size
    img = img.crop((left, top, right, bottom))

    # Step 3: Convert the image to a NumPy array and scale pixel values to [0, 1]
    img_array = np.array(img).astype(np.float32) / 255.0

    # Step 4: Normalize the image
    mean = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
    std = np.array(std, dtype=np.float32).reshape(1, 1, 3)
    img_array = (img_array - mean) / std

    # Step 5: Change the order of dimensions from (H, W, C) to (C, H, W)
    img_array = np.transpose(img_array, (2, 0, 1))
    return img_array


class ImageClassifier:
    def __init__(self, name: str, label_names: list[str]):
        self.name: str = name
        self.label_names = label_names

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
        image_array = classify_transforms(image)
        image_array = np.expand_dims(image_array, axis=0)

        grpc_stub = get_triton_inference_stub(triton_uri)
        request = service_pb2.ModelInferRequest()
        request.model_name = self.name

        image_input = service_pb2.ModelInferRequest().InferInputTensor()
        image_input.name = "images"

        image_input.datatype = "FP32"

        image_input.shape.extend([1, 3, 224, 224])
        request.inputs.extend([image_input])

        output = service_pb2.ModelInferRequest().InferRequestedOutputTensor()
        output.name = "output0"
        request.outputs.extend([output])

        request.raw_input_contents.extend([image_array.tobytes()])
        start_time = time.monotonic()
        response = grpc_stub.ModelInfer(request)
        latency = time.monotonic() - start_time

        logger.debug("Inference time for %s: %s", self.name, latency)

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
        ).reshape((1, len(self.label_names)))[0]

        score_indices = np.argsort(-output)

        latency = time.monotonic() - start_time
        logger.debug("Post-processing time for %s: %s", self.name, latency)
        return [(self.label_names[i], float(output[i])) for i in score_indices]
