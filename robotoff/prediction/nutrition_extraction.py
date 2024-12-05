import dataclasses
import functools
import re
import typing
from collections import Counter
from pathlib import Path

import numpy as np
from openfoodfacts.ocr import OCRResult
from openfoodfacts.utils import load_json
from PIL import Image
from transformers import AutoProcessor, BatchEncoding, PreTrainedTokenizerBase
from tritonclient.grpc import service_pb2

from robotoff import settings
from robotoff.triton import (
    GRPCInferenceServiceStub,
    add_triton_infer_input_tensor,
    get_triton_inference_stub,
)
from robotoff.types import JSONType
from robotoff.utils.logger import get_logger

logger = get_logger(__name__)

MODEL_NAME = "nutrition_extractor"
MODEL_VERSION = f"{MODEL_NAME}-1.0"

# The tokenizer assets are stored in the model directory
MODEL_DIR = settings.TRITON_MODELS_DIR / f"{MODEL_NAME}/1/model.onnx"


@dataclasses.dataclass
class NutrientPrediction:
    entity: str
    text: str
    value: str | None
    unit: str | None
    score: float
    start: int
    end: int
    char_start: int
    char_end: int


@dataclasses.dataclass
class NutritionEntities:
    raw: list[dict]
    aggregated: list[dict]
    postprocessed: list[dict]


@dataclasses.dataclass
class NutritionExtractionPrediction:
    nutrients: dict[str, NutrientPrediction]
    entities: NutritionEntities


def predict(
    image: Image.Image,
    ocr_result: OCRResult,
    model_version: str = "1",
    triton_uri: str | None = None,
) -> NutritionExtractionPrediction | None:
    """Predict the nutrient values from an image and an OCR result.

    The function returns a `NutritionExtractionPrediction` object with the following
    fields:

    - `nutrients`: a dictionary mapping nutrient names to `NutrientPrediction` objects
    - `entities`: a `NutritionEntities` object containing the raw, aggregated and
        postprocessed entities

    If the OCR result does not contain any text annotation, the function returns
    `None`.

    :param image: the *original* image (not resized)
    :param ocr_result: the OCR result
    :param model_version: the version of the model to use, defaults to "1"
    :param triton_uri: the URI of the Triton Inference Server, if not provided, the
        default value from settings is used
    :return: a `NutritionExtractionPrediction` object
    """
    triton_stub = get_triton_inference_stub(triton_uri)
    id2label = get_id2label(MODEL_DIR)
    processor = get_processor(MODEL_DIR)

    preprocess_result = preprocess(image, ocr_result, processor)

    if preprocess_result is None:
        return None

    words, char_offsets, _, batch_encoding = preprocess_result
    logits = send_infer_request(
        input_ids=batch_encoding.input_ids,
        attention_mask=batch_encoding.attention_mask,
        bbox=batch_encoding.bbox,
        pixel_values=batch_encoding.pixel_values,
        model_name=MODEL_NAME,
        triton_stub=triton_stub,
        model_version=model_version,
    )
    return postprocess(logits[0], words, char_offsets, batch_encoding, id2label)


def preprocess(
    image: Image.Image, ocr_result: OCRResult, processor
) -> (
    tuple[
        list[str], list[tuple[int, int]], list[tuple[int, int, int, int]], BatchEncoding
    ]
    | None
):
    """Preprocess an image and OCR result for the LayoutLMv3 model.

    The *original* image must be provided, as we use the image size to normalize
    the bounding boxes.

    The function returns a tuple containing the following elements:

    - `words`: a list of words
    - `char_offsets`: a list of character offsets
    - `bboxes`: a list of bounding boxes
    - `batch_encoding`: the BatchEncoding returned by the tokenizer

    If the OCR result does not contain any text annotation, the function returns
    `None`.

    :param image: the original image
    :param ocr_result: the OCR result
    :param processor: the LaymoutLM processor
    :return: a tuple containing the words, character offsets, bounding boxes and
        BatchEncoding
    """
    if not ocr_result.full_text_annotation:
        return None

    words = []
    char_offsets = []
    bboxes = []

    if image.mode != "RGB":
        image = image.convert("RGB")

    width, height = image.size
    for page in ocr_result.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    words.append(word.text)
                    char_offsets.append((word.start_idx, word.end_idx))
                    vertices = word.bounding_poly.vertices
                    # LayoutLM requires an integer between 0 and 1000 (excluded)
                    # for the dataset
                    x_min = int(min(v[0] for v in vertices) * 1000 / width)
                    x_max = int(max(v[0] for v in vertices) * 1000 / width)
                    y_min = int(min(v[1] for v in vertices) * 1000 / height)
                    y_max = int(max(v[1] for v in vertices) * 1000 / height)
                    bboxes.append(
                        (
                            max(0, min(999, x_min)),
                            max(0, min(999, y_min)),
                            max(0, min(999, x_max)),
                            max(0, min(999, y_max)),
                        )
                    )

    batch_encoding = processor(
        [image],
        [words],
        boxes=[bboxes],
        truncation=True,
        padding=False,
        return_tensors="np",
        return_offsets_mapping=True,
        return_special_tokens_mask=True,
    )
    return words, char_offsets, bboxes, batch_encoding


def postprocess(
    logits: np.ndarray,
    words: list[str],
    char_offsets: list[tuple[int, int]],
    batch_encoding: BatchEncoding,
    id2label: dict[int, str],
) -> NutritionExtractionPrediction:
    """Postprocess the model output to extract the nutrient predictions.

    The function returns a `NutritionExtractionPrediction` object with the following
    fields:

    - `nutrients`: a dictionary mapping nutrient names to `NutrientPrediction` objects
    - `entities`: a `NutritionEntities` object containing the raw, aggregated and
        postprocessed entities

    :param logits: the predicted logits
    :param words: the words corresponding to the input
    :param char_offsets: the character offsets of the words
    :param batch_encoding: the BatchEncoding returned by the tokenizer
    :param id2label: a dictionary mapping label IDs to label names
    :return: a `NutritionExtractionPrediction` object
    """
    pre_entities = gather_pre_entities(
        logits, words, char_offsets, batch_encoding, id2label
    )
    aggregated_entities = aggregate_entities(pre_entities)
    postprocessed_entities = postprocess_aggregated_entities(aggregated_entities)
    return NutritionExtractionPrediction(
        nutrients={
            entity["entity"]: NutrientPrediction(
                **{k: v for k, v in entity.items() if k != "valid"}
            )
            for entity in postprocessed_entities
            if entity["valid"]
        },
        entities=NutritionEntities(
            raw=pre_entities,
            aggregated=aggregated_entities,
            postprocessed=postprocessed_entities,
        ),
    )


def gather_pre_entities(
    logits: np.ndarray,
    words: list[str],
    char_offsets: list[tuple[int, int]],
    batch_encoding: BatchEncoding,
    id2label: dict[int, str],
) -> list[JSONType]:
    """Gather the pre-entities extracted by the model.

    This function takes as input the predicted logits returned by the model and
    additional preprocessing outputs (words, char_offsets, batch_encoding) and returns a
    list of pre-entities with the following fields:

    - `word`: the word corresponding to the entity (string)
    - `entity`: the entity type (string, ex: "ENERGY_KCAL_100G")
    - `score`: the score of the entity (float)
    - `index`: the index of the word in the input
    - `char_start`: the character start index of the entity
    - `char_end`: the character end index of the entity

    :param logits: the predicted logits
    :param words: the words corresponding to the input
    :param char_offsets: the character offsets of the words
    :param batch_encoding: the BatchEncoding returned by the tokenizer
    :param id2label: a dictionary mapping label IDs to label names
    :return: a list of pre-entities
    """
    special_tokens_mask = batch_encoding.special_tokens_mask[0]

    maxes = np.max(logits, axis=-1, keepdims=True)
    shifted_exp = np.exp(logits - maxes)
    scores = shifted_exp / shifted_exp.sum(axis=-1, keepdims=True)
    label_ids = logits.argmax(axis=-1)

    pre_entities = []
    previous_word_id = None
    word_ids = batch_encoding.word_ids()

    for idx in range(len(scores)):
        # idx may be out of bounds if the input_ids are padded
        # word_id corresponds to the index of the input words, while
        # idx is the index of the token. A word can have multiple tokens
        # if it is split into subwords.
        word_id = word_ids[idx] if idx < len(word_ids) else None
        # Filter special_tokens (BOS, EOS, PAD)
        if special_tokens_mask[idx]:
            previous_word_id = word_id
            continue

        # The token is a subword if it has the same word_id as the previous token
        is_subword = word_id == previous_word_id
        if int(batch_encoding.input_ids[0, idx]) == 3:  # unknown token
            is_subword = False

        if is_subword:
            # If the token is a subword, we skip it
            # The entity will be attached to the first token of the word
            # and the score will be the score of the first token
            continue

        previous_word_id = word_id
        word = words[word_id]
        label_id = label_ids[idx]
        score = float(scores[idx, label_id])
        label = id2label[label_id]
        # As the entities are very short (< 3 tokens most of the time) and as
        # two entities with the same label are in practice never adjacent,
        # we simplify the schema by ignoring the B- and I- prefix.
        # It simplifies processing and makes it more robust against model
        # prefix mis-predictions.
        entity = label.split("-", maxsplit=1)[-1]

        pre_entity = {
            "word": word,
            "entity": entity,
            "score": score,
            "index": word_id,
            "char_start": char_offsets[word_id][0],
            "char_end": char_offsets[word_id][1],
        }
        pre_entities.append(pre_entity)
    return pre_entities


def aggregate_entities(pre_entities: list[JSONType]) -> list[JSONType]:
    """Aggregate the entities extracted by the model.

    This function takes as input the list of pre-entities (see the
    `gather_pre_entities` function) and aggregate them into entities with the
    following fields:

    - `entity`: the entity type (string, ex: "ENERGY_KCAL_100G")
    - `words`: the words forming the entity (list of strings)
    - `score`: the score of the entity (float), we use the score of the first token
    - `start`: the token start index of the entity
    - `end`: the token end index of the entity
    - `char_start`: the character start index of the entity
    - `char_end`: the character end index of the entity

    The entities are aggregated by grouping consecutive tokens with the same entity
    type.
    """
    entities = []

    current_entity = None
    for pre_entity in pre_entities:
        if pre_entity["entity"] == "O":
            if current_entity is not None:
                entities.append(current_entity)
                current_entity = None
            continue

        if current_entity is None:
            current_entity = {
                "entity": pre_entity["entity"],
                "words": [pre_entity["word"]],
                # We use the score of the first word as the score of the entity
                "score": pre_entity["score"],
                "start": pre_entity["index"],
                "end": pre_entity["index"] + 1,
                "char_start": pre_entity["char_start"],
                "char_end": pre_entity["char_end"],
            }
            continue

        if current_entity["entity"] == pre_entity["entity"]:
            current_entity["words"].append(pre_entity["word"])
            current_entity["end"] = pre_entity["index"] + 1
            current_entity["char_end"] = pre_entity["char_end"]
            continue

        # If we reach this point, the entity has changed
        entities.append(current_entity)
        current_entity = {
            "entity": pre_entity["entity"],
            "words": [pre_entity["word"]],
            "score": pre_entity["score"],
            "start": pre_entity["index"],
            "end": pre_entity["index"] + 1,
            "char_start": pre_entity["char_start"],
            "char_end": pre_entity["char_end"],
        }

    if current_entity is not None:
        entities.append(current_entity)

    return entities


def postprocess_aggregated_entities(
    aggregated_entities: list[JSONType],
) -> list[JSONType]:
    """Postprocess the aggregated entities to extract the nutrient values.

    This function takes as input the list of aggregated entities (see the
    `aggregate_entities` function) and add the following fields to each entity:

    - `value`: the nutrient value (string, ex: "12.5")
    - `unit`: the nutrient unit (string, ex: "g")
    - `valid`: a boolean indicating whether the entity is valid or not
    - `invalid_reason`: a string indicating the reason why the entity is invalid
    - `text`: the text of the entity

    The field `words` is removed from the aggregated entities.

    Some additional postprocessing steps are also performed to try to fix specific
    errors:

    - The OCR engine can split incorrectly tokens for energy nutrients
    - The OCR engine can fail to detect the word corresponding to the unit after the
      value
    - The OCR mistakenly detected the 'g' unit as a '9'
    """
    postprocessed_entities = []

    for entity in aggregated_entities:
        postprocessed_entity = postprocess_aggregated_entities_single(entity)
        postprocessed_entities.append(postprocessed_entity)

    entity_type_multiple = set(
        entity
        for entity, count in Counter(
            entity["entity"] for entity in postprocessed_entities
        ).items()
        if count > 1
    )
    for postprocessed_entity in postprocessed_entities:
        if postprocessed_entity["entity"] in entity_type_multiple:
            postprocessed_entity["valid"] = False
            postprocessed_entity["invalid_reason"] = "multiple_entities"

    return postprocessed_entities


SERVING_SIZE_MISSING_G = re.compile(r"([0-9]+[,.]?[0-9]*)\s*9")


def postprocess_aggregated_entities_single(entity: JSONType) -> JSONType:
    """Postprocess a single aggregated entity and return an entity with the extracted
    information. This is the first step in the postprocessing of aggregated entities.

    For each aggregated entity, we return the following fields:

    - `value`: the nutrient value (string, ex: "12.5")
    - `unit`: the nutrient unit (string, ex: "g")
    - `valid`: a boolean indicating whether the entity is valid or not
    - `text`: the text of the entity

    The field `words` is removed from the aggregated entities.

    Some additional postprocessing steps are also performed to try to fix specific
    errors:

    - The OCR engine can split incorrectly tokens for energy nutrients
    - The OCR engine can fail to detect the word corresponding to the unit after the
      value
    - The OCR mistakenly detected the 'g' unit as a '9'
    """
    words = [word.strip().strip("()/") for word in entity["words"]]
    entity_label = entity["entity"].lower()

    if entity_label == "serving_size":
        entity_base = None
        entity_per = None
        full_entity_label = entity_label
    else:
        # Reformat the nutrient name so that it matches Open Food Facts format
        # Ex: "ENERGY_KCAL_100G" -> "energy-kcal_100g"
        entity_base, entity_per = entity_label.rsplit("_", 1)
        entity_base = entity_base.replace("_", "-")
        full_entity_label = f"{entity_base}_{entity_per}"

    if entity_label.startswith("energy_"):
        # Due to incorrect token split by the OCR, the unit (kcal or kj) can be
        # attached to the next token.
        # Ex: "525 kJ/126 kcal" is often tokenized into ["525", "kJ/"126", "kcal"]
        # We handle this case here.
        if len(words[0]) > 3 and words[0][:3].lower() == "kj/":
            words[0] = words[0][3:]

    words_str = " ".join(words)
    value = None
    unit = None
    is_valid = True

    if entity_label == "serving_size":
        value = words_str
        # Sometimes the unit 'g' in the `serving_size is detected as a '9'
        # In such cases, we replace the '9' with 'g'
        match = SERVING_SIZE_MISSING_G.match(value)
        if match:
            value = f"{match.group(1)} g"
    elif words_str in ("trace", "traces"):
        value = "traces"
    else:
        value, unit, is_valid = match_nutrient_value(words_str, entity_label)

    return {
        "entity": full_entity_label,
        "text": words_str,
        "value": value,
        "unit": unit,
        "score": entity["score"],
        "start": entity["start"],
        "end": entity["end"],
        "char_start": entity["char_start"],
        "char_end": entity["char_end"],
        "valid": is_valid,
    }


# We match "O" to handle the case where the OCR engine failed to
# recognize correctly "0" (zero) and uses "O" (letter O) instead
NUTRIENT_VALUE_REGEX = re.compile(
    r"(< ?)?((?:[0-9]+[,.]?[0-9]*)|O) ?(g|mg|µg|mcg|kj|kcal)?", re.I
)


def match_nutrient_value(
    words_str: str, entity_label: str
) -> tuple[str | None, str | None, bool]:
    """From an entity label and the words forming the entity, extract the nutrient
    value, the unit and a boolean indicating whether the entity is valid or not.

    The function returns a tuple containing the following elements:

    - `value`: the nutrient value (string, ex: "12.5")
    - `unit`: the nutrient unit (string, ex: "g")
    - `is_valid`: a boolean indicating whether the entity is valid or not

    In case we could not extract the nutrient value, the function returns `None` for the
    value and the unit and `False` for the validity.
    Otherwise, the value is never null but the unit can be null if the OCR engine didn't
    detect the unit after the value.

    :param words_str: the words forming the entity
    :param entity_label: the entity label
    :return: a tuple containing the value, the unit and a boolean indicating whether the
        entity is valid or not
    """
    match = NUTRIENT_VALUE_REGEX.search(words_str)

    if not match:
        logger.warning("Could not extract nutrient value from %s", words_str)
        return None, None, False

    prefix = match.group(1)
    value = match.group(2).replace(",", ".")

    if prefix is not None:
        prefix = prefix.strip()
        value = f"{prefix} {value}"

    if value == "O":
        # The OCR engine failed to recognize correctly "0" (zero) and uses
        # "O" (letter O) instead
        value = "0"
    unit = match.group(3)
    # Unit can be none if the OCR engine didn't detect the unit after the
    # value as a word
    if unit is None:
        if entity_label.startswith("energy_"):
            # Due to incorrect splitting by OCR engine, we don't necessarily
            # have a unit for energy, but as the entity can only have a
            # single unit (kcal or kJ), we infer the unit from the entity
            # name
            # `entity_label` is in the form "energy_kcal_100g", so we can
            # extract the unit from the 2nd part (index 1) of the entity name
            unit = entity_label.split("_")[1].lower()
        if (
            any(
                entity_label.startswith(target)
                for target in (
                    "proteins",
                    "sugars",
                    "carbohydrates",
                    "fat",
                    "fiber",
                    "salt",
                    # we use "_" here as separator as '-' is only used in
                    # Product Opener, the label names are all separated by '_'
                    "saturated_fat",
                    "added_sugars",
                    "trans_fat",
                )
            )
            and value.endswith("9")
            and "." in value
            and not value.endswith(".9")
        ):
            unit = "g"
            value = value[:-1]
    else:
        unit = unit.lower()
        if unit == "mcg":
            unit = "µg"

    return value, unit, True


@functools.cache
def get_processor(model_dir: Path) -> PreTrainedTokenizerBase:
    """Return the processor located in `model_dir`.

    The processor is only loaded once and then cached in memory.

    :param model_dir: the model directory
    :return: the processor
    """
    return AutoProcessor.from_pretrained(model_dir)


@functools.cache
def get_id2label(model_dir: Path) -> dict[int, str]:
    """Return a dictionary mapping label IDs to labels for a model located in
    `model_dir`."""
    config_path = model_dir / "config.json"

    if not config_path.exists():
        raise ValueError(f"Model config not found in {model_dir}")

    id2label = typing.cast(dict, load_json(config_path))["id2label"]
    return {int(k): v for k, v in id2label.items()}


def send_infer_request(
    input_ids: np.ndarray,
    attention_mask: np.ndarray,
    bbox: np.ndarray,
    pixel_values: np.ndarray,
    model_name: str,
    triton_stub: GRPCInferenceServiceStub,
    model_version: str = "1",
) -> np.ndarray:
    """Send a NER infer request to the Triton inference server.

    The first dimension of `input_ids` and `attention_mask` must be the batch
    dimension. This function returns the predicted logits.

    :param input_ids: input IDs, generated using the transformers tokenizer.
    :param attention_mask: attention mask, generated using the transformers
        tokenizer.
    :param bbox: bounding boxes of the tokens, generated using the transformers
        tokenizer.
    :param pixel_values: pixel values of the image, generated using the
        transformers tokenizer.
    :param model_name: the name of the model to use
    :param model_version: version of the model model to use, defaults to "1"
    :return: the predicted logits
    """
    request = build_triton_request(
        input_ids=input_ids,
        attention_mask=attention_mask,
        bbox=bbox,
        pixel_values=pixel_values,
        model_name=model_name,
        model_version=model_version,
    )
    response = triton_stub.ModelInfer(request)
    num_tokens = response.outputs[0].shape[1]
    num_labels = response.outputs[0].shape[2]
    return np.frombuffer(
        response.raw_output_contents[0],
        dtype=np.float32,
    ).reshape((len(input_ids), num_tokens, num_labels))


def build_triton_request(
    input_ids: np.ndarray,
    attention_mask: np.ndarray,
    bbox: np.ndarray,
    pixel_values: np.ndarray,
    model_name: str,
    model_version: str = "1",
):
    """Build a Triton ModelInferRequest gRPC request for LayoutLMv3 models.

    :param input_ids: input IDs, generated using the transformers tokenizer.
    :param attention_mask: attention mask, generated using the transformers
        tokenizer.
    :param bbox: bounding boxes of the tokens, generated using the transformers
        tokenizer.
    :param pixel_values: pixel values of the image, generated using the
        transformers tokenizer.
    :param model_name: the name of the model to use.
    :param model_version: version of the model model to use, defaults to "1".
    :return: the gRPC ModelInferRequest
    """
    request = service_pb2.ModelInferRequest()
    request.model_name = model_name
    request.model_version = model_version

    add_triton_infer_input_tensor(request, "input_ids", input_ids, "INT64")
    add_triton_infer_input_tensor(request, "attention_mask", attention_mask, "INT64")
    add_triton_infer_input_tensor(request, "bbox", bbox, "INT64")
    add_triton_infer_input_tensor(request, "pixel_values", pixel_values, "FP32")

    return request
