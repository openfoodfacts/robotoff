import functools
import struct

import grpc
import numpy as np
from more_itertools import chunked
from PIL import Image
from transformers import CLIPImageProcessor
from tritonclient.grpc import service_pb2, service_pb2_grpc

from robotoff import settings
from robotoff.utils import get_logger

logger = get_logger(__name__)

# Maximum batch size for CLIP model set in CLIP config.pbtxt
CLIP_MAX_BATCH_SIZE = 32


@functools.cache
def get_triton_inference_stub() -> service_pb2_grpc.GRPCInferenceServiceStub:
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

    for image_batch in chunked(images, CLIP_MAX_BATCH_SIZE):
        request = generate_clip_embedding_request(image_batch)
        response = stub.ModelInfer(request)
        embedding_batch = np.frombuffer(
            response.raw_output_contents[0],
            dtype=np.float32,
        ).reshape((len(image_batch), -1))
        embedding_batches.append(embedding_batch)

    return np.concatenate(embedding_batches)


def deserialize_byte_tensor(data: bytes) -> list[str]:
    """Deserialize a byte tensor into a list of string.

    This is used to deserialize string array outputs from Triton models.
    """
    offset = 0
    # 4 bytes are used to encode string length
    int_byte_len = 4
    array = []
    while len(data) >= offset + int_byte_len:
        str_length = struct.unpack("<I", data[offset : offset + int_byte_len])[0]
        offset += int_byte_len
        string_data = data[offset : offset + str_length].decode("utf-8")
        offset += str_length
        array.append(string_data)
    return array


# Copied from triton client repository
def serialize_byte_tensor(input_tensor):
    """
    Serializes a bytes tensor into a flat numpy array of length prepended
    bytes. The numpy array should use dtype of np.object_. For np.bytes_,
    numpy will remove trailing zeros at the end of byte sequence and because
    of this it should be avoided.
    Parameters
    ----------
    input_tensor : np.array
        The bytes tensor to serialize.
    Returns
    -------
    serialized_bytes_tensor : np.array
        The 1-D numpy array of type uint8 containing the serialized bytes in 'C' order.
    Raises
    ------
    InferenceServerException
        If unable to serialize the given tensor.
    """

    if input_tensor.size == 0:
        return ()

    # If the input is a tensor of string/bytes objects, then must flatten those
    # into a 1-dimensional array containing the 4-byte byte size followed by the
    # actual element bytes. All elements are concatenated together in "C" order.
    if (input_tensor.dtype == np.object_) or (input_tensor.dtype.type == np.bytes_):
        flattened_ls = []
        for obj in np.nditer(input_tensor, flags=["refs_ok"], order="C"):
            # If directly passing bytes to BYTES type,
            # don't convert it to str as Python will encode the
            # bytes which may distort the meaning
            if input_tensor.dtype == np.object_:
                if type(obj.item()) == bytes:
                    s = obj.item()
                else:
                    s = str(obj.item()).encode("utf-8")
            else:
                s = obj.item()
            flattened_ls.append(struct.pack("<I", len(s)))
            flattened_ls.append(s)
        flattened = b"".join(flattened_ls)
        return flattened
    return None
