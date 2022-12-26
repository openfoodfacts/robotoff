import cachetools
import grpc
import numpy as np
from more_itertools import chunked
from PIL import Image
from transformers import CLIPImageProcessor
from tritonclient.grpc import service_pb2, service_pb2_grpc

from robotoff import settings
from robotoff.utils import get_logger

logger = get_logger(__name__)


@cachetools.cached(cachetools.Cache(maxsize=1))
def get_triton_inference_stub():
    channel = grpc.insecure_channel(settings.TRITON_URI)
    return service_pb2_grpc.GRPCInferenceServiceStub(channel)


def generate_clip_embedding_request(images: list[Image.Image]):
    processor = CLIPImageProcessor()
    inputs = processor(images=images, return_tensors="np", padding=True).pixel_values
    request = service_pb2.ModelInferRequest()
    request.model_name = "clip"

    image_input = service_pb2.ModelInferRequest().InferInputTensor()
    image_input.name = "pixel_values"
    image_input.datatype = "FP32"
    image_input.shape.extend(list(inputs.shape))
    request.inputs.extend([image_input])

    # attention_mask
    attention_mask_input = service_pb2.ModelInferRequest().InferInputTensor()
    attention_mask_input.name = "attention_mask"
    attention_mask_input.datatype = "INT64"
    attention_mask_input.shape.extend([len(images), 2])
    request.inputs.extend([attention_mask_input])

    # input_ids
    input_id_input = service_pb2.ModelInferRequest().InferInputTensor()
    input_id_input.name = "input_ids"
    input_id_input.datatype = "INT64"
    input_id_input.shape.extend([len(images), 2])
    request.inputs.extend([input_id_input])

    output = service_pb2.ModelInferRequest().InferRequestedOutputTensor()
    output.name = "image_embeds"
    request.outputs.extend([output])

    request.raw_input_contents.extend([inputs.tobytes()])
    # We're not interested in text embedding generation but we must provide
    # attention_mask and input_ids anyway, so we provide an empty text
    # ([BOS, EOS] input_ids) with [1, 1] attention mask
    request.raw_input_contents.extend([np.ones((len(images), 2), dtype=int).tobytes()])
    request.raw_input_contents.extend(
        [(np.ones((len(images), 2), dtype=int) * [49406, 49407]).tobytes()]
    )
    return request


def generate_clip_embedding(images: list[Image.Image]) -> np.ndarray:
    embedding_batches = []
    stub = get_triton_inference_stub()
    # max_batch_size is currently set to default value of 4 for CLIP
    # TODO(raphael): Supply a custom model config file to increase this
    # value
    for image_batch in chunked(images, 4):
        request = generate_clip_embedding_request(image_batch)
        response = stub.ModelInfer(request)
        embedding_batch = np.frombuffer(
            response.raw_output_contents[0],
            dtype=np.float32,
        ).reshape((len(image_batch), -1))
        embedding_batches.append(embedding_batch)

    return np.concatenate(embedding_batches)
