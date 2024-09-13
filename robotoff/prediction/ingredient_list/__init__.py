import dataclasses
import functools
from pathlib import Path
from typing import Union

import numpy as np
from openfoodfacts.ocr import OCRResult
from transformers import AutoTokenizer, PreTrainedTokenizerBase
from tritonclient.grpc import service_pb2

from robotoff import settings
from robotoff.prediction.ingredient_list.postprocess import detect_additional_mentions
from robotoff.prediction.langid import LanguagePrediction, predict_lang_batch
from robotoff.triton import GRPCInferenceServiceStub, get_triton_inference_stub
from robotoff.utils import http_session

from .transformers_pipeline import AggregationStrategy, TokenClassificationPipeline

# The tokenizer assets are stored in the model directory
INGREDIENT_NER_MODEL_DIR = settings.TRITON_MODELS_DIR / "ingredient-ner/1/model.onnx"

INGREDIENT_ID2LABEL = {0: "O", 1: "B-ING", 2: "I-ING"}

MODEL_NAME = "ingredient-detection"
MODEL_VERSION = "ingredient-detection-1.0"


@dataclasses.dataclass
class IngredientPredictionAggregatedEntity:
    # character start index of the entity
    start: int
    # character end index of the entity
    end: int
    # character start index of the entity, before postprocessing (i.e.
    # before adding organic or allergen mentions)
    raw_end: int
    # confidence score
    score: float
    # entity text (without organic or allergen mentions)
    text: str
    # language prediction of the entity text
    lang: LanguagePrediction | None = None
    # the bounding box of the entity in absolute coordinates
    # (y_min, x_min, y_max, x_max), or None if not available
    bounding_box: tuple[int, int, int, int] | None = None


@dataclasses.dataclass
class IngredientPredictionRawEntity:
    # entity label (either 'B-ING' or 'I-ING')
    entity: str
    # confidence score
    score: float
    # index of the token
    index: int
    # character start index of the token
    start: int
    # character end index of the token
    end: int
    # token string
    word: str


@dataclasses.dataclass
class IngredientPredictionOutput:
    # list of detected entities, either a list of
    # `IngredientPredictionRawEntity` (if aggregation_strategy ==
    # AggregationStrategy.None) or a list of
    # `IngredientPredictionAggregatedEntity` otherwise
    entities: Union[
        list[IngredientPredictionRawEntity], list[IngredientPredictionAggregatedEntity]
    ]
    # Original input text
    text: str


def predict_from_ocr(
    input_ocr: str | OCRResult,
    aggregation_strategy: AggregationStrategy = AggregationStrategy.FIRST,
    predict_lang: bool = True,
    model_version: str = "1",
    triton_uri: str | None = None,
) -> IngredientPredictionOutput:
    """Predict ingredient lists from an OCR.

    :param input_ocr: the URL of the OCR JSON file or the OCRResult to use
    :param aggregation_strategy: the aggregation strategy to use, defaults to
        AggregationStrategy.FIRST.
    :param predict_lang: if True, populate the `lang` field in
        `IngredientPredictionAggregatedEntity`. This flag is ignored if
        `aggregation_strategy` is `NONE`.
    :param model_version: version of the model model to use, defaults to "1"
    :param triton_uri: URI of the Triton Inference Server, defaults to None. If
        not provided, the default value from settings is used.
    :return: the `IngredientPredictionOutput`
    """
    ocr_result: OCRResult
    if isinstance(input_ocr, str):
        # `input_ocr` is a URL, fetch OCR JSON and get OCRResult
        ocr_result = OCRResult.from_url(input_ocr, http_session, error_raise=True)  # type: ignore
    else:
        ocr_result = input_ocr

    text = ocr_result.get_full_text_contiguous()
    if not text:
        return IngredientPredictionOutput(entities=[], text=text)  # type: ignore

    triton_stub = get_triton_inference_stub(triton_uri)
    predictions = predict_batch(
        [text], triton_stub, aggregation_strategy, predict_lang, model_version
    )
    prediction = predictions[0]

    for entity in prediction.entities:
        if isinstance(entity, IngredientPredictionAggregatedEntity):
            # Add the bounding box to the entity
            entity.bounding_box = ocr_result.get_match_bounding_box(
                entity.start, entity.end
            )

    return prediction


@functools.cache
def get_tokenizer(model_dir: Path) -> PreTrainedTokenizerBase:
    """Return the tokenizer located in `model_dir`.

    The tokenizer is only loaded once and then cached in memory.

    :param model_dir: the model directory
    :return: the tokenizer
    """
    return AutoTokenizer.from_pretrained(model_dir)


def predict_batch(
    texts: list[str],
    triton_stub: GRPCInferenceServiceStub,
    aggregation_strategy: AggregationStrategy = AggregationStrategy.FIRST,
    predict_lang: bool = True,
    model_version: str = "1",
) -> list[IngredientPredictionOutput]:
    """Predict ingredient lists from a batch of texts using the NER model.

    :param texts: a list of strings
    :param triton_stub: the Triton gRPC inference service stub
    :param aggregation_strategy: the aggregation strategy to use, defaults to
        AggregationStrategy.FIRST. See the HuggingFace documentation:
        https://huggingface.co/docs/transformers/main_classes/pipelines#transformers.TokenClassificationPipeline
    :param predict_lang: if True, populate the `lang` field in
        `IngredientPredictionAggregatedEntity`. This flag is ignored if
        `aggregation_strategy` is `NONE`.
    :param model_version: version of the model model to use, defaults to "1"
    :return: a list of IngredientPredictionOutput (one for each input text)
    """
    tokenizer = get_tokenizer(INGREDIENT_NER_MODEL_DIR)
    # The postprocessing pipeline required `offsets_mapping` and
    # `special_tokens_mask``
    batch_encoding = tokenizer(
        texts,
        truncation=True,
        padding=True,
        return_tensors="np",
        return_offsets_mapping=True,
        return_special_tokens_mask=True,
    )
    logits = send_ner_infer_request(
        batch_encoding.input_ids,
        batch_encoding.attention_mask,
        "ingredient-ner",
        triton_stub=triton_stub,
        model_version=model_version,
    )
    pipeline = TokenClassificationPipeline(tokenizer, INGREDIENT_ID2LABEL)

    outputs = []
    for idx in range(len(texts)):
        sentence = texts[idx]
        model_outputs = {
            "sentence": sentence,
            "logits": logits[idx],
            "input_ids": batch_encoding.input_ids[idx],
            "offset_mapping": batch_encoding.offset_mapping[idx],
            "special_tokens_mask": batch_encoding.special_tokens_mask[idx],
            "word_ids": batch_encoding.word_ids(idx),
        }
        pipeline_output = pipeline.postprocess(model_outputs, aggregation_strategy)

        if aggregation_strategy is AggregationStrategy.NONE:
            raw_entities = [
                IngredientPredictionRawEntity(
                    entity=entity["entity"],
                    score=float(entity["score"]),
                    index=int(entity["index"]),
                    start=int(entity["start"]),
                    end=int(entity["end"]),
                    word=entity["word"],
                )
                for entity in pipeline_output
            ]
        else:
            agg_entities = []
            for output in pipeline_output:
                start = int(output["start"])
                raw_end = int(output["end"])
                end = detect_additional_mentions(sentence, raw_end)
                text = sentence[start:end]
                agg_entities.append(
                    IngredientPredictionAggregatedEntity(
                        start=start,
                        end=end,
                        raw_end=raw_end,
                        score=float(output["score"]),
                        text=text,
                    ),
                )
            if predict_lang:
                texts = [entity.text for entity in agg_entities]
                for i, language_predictions in enumerate(
                    predict_lang_batch(texts, k=1)
                ):
                    agg_entities[i].lang = language_predictions[0]

        entities: Union[
            list[IngredientPredictionRawEntity],
            list[IngredientPredictionAggregatedEntity],
        ] = (
            raw_entities
            if aggregation_strategy is AggregationStrategy.NONE
            else agg_entities
        )
        outputs.append(
            IngredientPredictionOutput(
                entities=entities,
                text=sentence,
            )
        )
    return outputs


def send_ner_infer_request(
    input_ids: np.ndarray,
    attention_mask: np.ndarray,
    model_name: str,
    triton_stub: GRPCInferenceServiceStub,
    model_version: str = "1",
) -> np.ndarray:
    """Send a NER infer request to the Triton inference server.

    The first dimension of `input_ids` and `attention_mask` must be the batch
    dimension. This function returns the predicted logits.

    :param input_ids: input IDs, generated using the transformers tokenizer
    :param attention_mask: attention mask, generated using the transformers
        tokenizer
    :param model_name: the name of the model to use
    :param model_version: version of the model model to use, defaults to "1"
    :return: the predicted logits
    """
    request = build_triton_request(input_ids, attention_mask, model_name, model_version)
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
    model_name: str,
    model_version: str = "1",
):
    """Build a Triton ModelInferRequest gRPC request.

    :param input_ids: input IDs, generated using the transformers tokenizer
    :param attention_mask: attention mask, generated using the transformers
        tokenizer
    :param model_name: the name of the model to use
    :return: the gRPC ModelInferRequest
    """
    request = service_pb2.ModelInferRequest()
    request.model_name = model_name
    request.model_version = model_version

    input_ids_input = service_pb2.ModelInferRequest().InferInputTensor()
    input_ids_input.name = "input_ids"
    input_ids_input.datatype = "INT64"
    input_ids_input.shape.extend(list(input_ids.shape))
    request.inputs.extend([input_ids_input])
    request.raw_input_contents.extend([input_ids.tobytes()])

    attention_mask_input = service_pb2.ModelInferRequest().InferInputTensor()
    attention_mask_input.name = "attention_mask"
    attention_mask_input.datatype = "INT64"
    attention_mask_input.shape.extend(list(attention_mask.shape))
    request.inputs.extend([attention_mask_input])
    request.raw_input_contents.extend([attention_mask.tobytes()])

    return request
