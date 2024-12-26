import functools
import json
import shutil
import struct
import tempfile
from pathlib import Path

import grpc
import numpy as np
from google.protobuf.json_format import MessageToJson
from huggingface_hub import snapshot_download
from more_itertools import chunked
from openfoodfacts.types import JSONType
from PIL import Image
from pydantic import BaseModel
from transformers import CLIPImageProcessor
from tritonclient.grpc import service_pb2, service_pb2_grpc
from tritonclient.grpc.service_pb2_grpc import GRPCInferenceServiceStub

from robotoff import settings
from robotoff.utils import get_logger

logger = get_logger(__name__)

# Maximum batch size for CLIP model set in CLIP config.pbtxt
CLIP_MAX_BATCH_SIZE = 32

# Useful Triton API endpoints:
# Get model config: /v2/models/{MODEL_NAME}/config


class HuggingFaceModel(BaseModel):
    name: str
    version: int
    repo_id: str
    subfolder: str = "onnx"
    revision: str = "main"


HUGGINGFACE_MODELS = [
    HuggingFaceModel(
        name="nutrition_extractor",
        version=1,
        repo_id="openfoodfacts/nutrition-extractor",
        revision="dea426bf3c3d289ad7b65d29a7744ea6851632a6",
    ),
    HuggingFaceModel(
        name="nutrition_extractor",
        version=2,
        repo_id="openfoodfacts/nutrition-extractor",
        revision="7a43f38725f50f37a8c7bce417fc75741bea49fe",
    ),
]


@functools.cache
def get_triton_inference_stub(
    triton_uri: str | None = None,
) -> GRPCInferenceServiceStub:
    """Return a gRPC stub for Triton Inference Server.

    If `triton_uri` is not provided, the default value from settings is used.

    :param triton_uri: URI of the Triton Inference Server, defaults to None
    :return: gRPC stub for Triton Inference Server
    """
    triton_uri = triton_uri or settings.TRITON_URI
    channel = grpc.insecure_channel(triton_uri)
    return service_pb2_grpc.GRPCInferenceServiceStub(channel)


def generate_clip_embedding_request(images: list[Image.Image]):
    processor = CLIPImageProcessor()
    inputs = processor(images=images, return_tensors="np").pixel_values
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


def generate_clip_embedding(
    images: list[Image.Image], triton_stub: GRPCInferenceServiceStub
) -> np.ndarray:
    embedding_batches = []
    for image_batch in chunked(images, CLIP_MAX_BATCH_SIZE):
        request = generate_clip_embedding_request(image_batch)
        response = triton_stub.ModelInfer(request)
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
        The 1-D numpy array of type uint8 containing the serialized bytes in
        'C' order.
    Raises
    ------
    InferenceServerException
        If unable to serialize the given tensor.
    """

    if input_tensor.size == 0:
        return ()

    # If the input is a tensor of string/bytes objects, then must flatten those
    # into a 1-dimensional array containing the 4-byte byte size followed by
    # the actual element bytes. All elements are concatenated together in "C"
    # order.
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


def add_triton_infer_input_tensor(request, name: str, data: np.ndarray, datatype: str):
    """Create and add an input tensor to a Triton gRPC Inference request.

    :param request: the Triton Inference request
    :param name: the name of the input tensor
    :param data: the input tensor data
    :param datatype: the datatype of the input tensor (e.g. "FP32")
    """
    input_tensor = service_pb2.ModelInferRequest().InferInputTensor()
    input_tensor.name = name
    input_tensor.datatype = datatype
    input_tensor.shape.extend(data.shape)
    request.inputs.extend([input_tensor])
    request.raw_input_contents.extend([data.tobytes()])


def load_model(
    triton_stub: GRPCInferenceServiceStub,
    model_name: str,
    model_version: str | None = None,
) -> None:
    """Load a model in Triton Inference Server.

    If the model was never loaded, it will be loaded with the default
    configuration generated by Triton.

    Otherwise, the behavior will depend on whether the `--model-version` option is
    provided:

    - If the option is provided, only the specified version will be loaded, the other
        versions will be unloaded.
    - If the option is not provided, the two latest versions will be loaded.

    :param triton_stub: gRPC stub for Triton Inference Server
    :param model_name: name of the model to load
    :param model_version: version of the model to load, defaults to None
    """
    request = service_pb2.RepositoryModelLoadRequest()
    request.model_name = model_name

    current_models = list_models(triton_stub)
    first_load = not any(
        model.name == model_name and model.state == "READY" for model in current_models
    )

    if first_load:
        logger.info("First load of model")
    else:
        logger.info("Previous model already loaded")
        model_config = json.loads(
            MessageToJson(get_model_config(triton_stub, model_name))
        )
        if model_version:
            logger.info(
                f"Model version specified, only loading that version ({model_version})"
            )
            version_policy: JSONType = {"specific": {"versions": [model_version]}}
        else:
            logger.info("No model version specified, loading 2 latest version")
            version_policy = {"latest": {"num_versions": 2}}

        request.parameters["config"].string_param = json.dumps(
            {
                "input": model_config["input"],
                "output": model_config["output"],
                "versionPolicy": version_policy,
                "max_batch_size": model_config["maxBatchSize"],
                "backend": model_config["backend"],
                "platform": model_config["platform"],
            }
        )

    triton_stub.RepositoryModelLoad(request)


def unload_model(triton_stub: GRPCInferenceServiceStub, model_name: str) -> None:
    """Unload completely a model from Triton Inference Server."""
    request = service_pb2.RepositoryModelUnloadRequest()
    request.model_name = model_name
    triton_stub.RepositoryModelUnload(request)


def list_models(triton_stub: GRPCInferenceServiceStub):
    request = service_pb2.RepositoryIndexRequest()
    response = triton_stub.RepositoryIndex(request)
    return response.models


def get_model_config(
    triton_stub: GRPCInferenceServiceStub,
    model_name: str,
    model_version: str | None = None,
):
    request = service_pb2.ModelConfigRequest()
    request.name = model_name
    if model_version:
        request.version = model_version

    response = triton_stub.ModelConfig(request)
    return response.config


def download_models():
    """Downloading all models from Hugging Face Hub.

    The models are downloaded in the Triton models directory. If the model
    already exists, it is not downloaded.
    """
    for model in HUGGINGFACE_MODELS:
        base_model_dir = settings.TRITON_MODELS_DIR / model.name
        base_model_dir.mkdir(parents=True, exist_ok=True)
        model_with_version_dir = base_model_dir / str(model.version) / "model.onnx"

        if model_with_version_dir.exists():
            logger.info(
                f"Model {model.name} version {model.version} already downloaded"
            )
            continue

        with tempfile.TemporaryDirectory() as temp_dir_str:
            logger.info(f"Temporary cache directory: {temp_dir_str}")
            temp_dir = Path(temp_dir_str)
            snapshot_download(
                repo_id=model.repo_id,
                allow_patterns=[f"{model.subfolder}/*"],
                revision=model.revision,
                local_dir=temp_dir,
            )
            model_with_version_dir.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Copying model files to {model_with_version_dir}")
            shutil.move(temp_dir / model.subfolder, model_with_version_dir)
