import csv
import dataclasses
import datetime
import functools
import hashlib
import io
import re
import tempfile
import typing
import urllib
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Literal, cast

import falcon
import orjson
import peewee
import requests
from falcon.media.validators import jsonschema
from openfoodfacts import OCRResult
from openfoodfacts.barcode import normalize_barcode
from openfoodfacts.images import extract_barcode_from_url
from openfoodfacts.ocr import OCRParsingException, OCRResultGenerationException
from openfoodfacts.types import COUNTRY_CODE_TO_NAME, Country
from PIL import Image
from sentry_sdk.integrations.falcon import FalconIntegration

from robotoff import settings
from robotoff.app import schema
from robotoff.app.auth import BasicAuthDecodeError, basic_decode, validate_token
from robotoff.app.core import (
    SkipVotedOn,
    SkipVotedType,
    filter_question_insight_types,
    get_image_predictions,
    get_images,
    get_insights,
    get_logo_annotation,
    get_predictions,
    save_annotation,
    update_logo_annotations,
    validate_params,
)
from robotoff.app.middleware import CacheClearMiddleware, DBConnectionMiddleware
from robotoff.batch import import_batch_predictions
from robotoff.elasticsearch import get_es_client
from robotoff.insights.extraction import (
    DEFAULT_OCR_PREDICTION_TYPES,
    extract_ocr_predictions,
)
from robotoff.insights.question import QuestionFormatter, QuestionFormatterFactory
from robotoff.logos import (
    generate_insights_from_annotated_logos,
    generate_insights_from_annotated_logos_job,
    knn_search,
)
from robotoff.models import (
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    LogoEmbedding,
    Prediction,
    ProductInsight,
    batch_insert,
    db,
)
from robotoff.off import OFFAuthentication, generate_image_path
from robotoff.prediction import image_classifier, ingredient_list, nutrition_extraction
from robotoff.prediction.category import predict_category
from robotoff.prediction.langid import predict_lang
from robotoff.prediction.object_detection import ObjectDetectionModelRegistry
from robotoff.products import get_product, get_product_dataset_etag
from robotoff.taxonomy import is_prefixed_value, match_taxonomized_value
from robotoff.types import (
    BatchJobType,
    ImageClassificationModel,
    InsightType,
    JSONType,
    NeuralCategoryClassifierModel,
    ObjectDetectionModel,
    PredictionType,
    ProductIdentifier,
    ServerType,
)
from robotoff.utils import get_image_from_url, get_logger, http_session
from robotoff.utils.i18n import TranslationStore
from robotoff.utils.text import get_tag
from robotoff.workers.queues import enqueue_job, get_high_queue, low_queue
from robotoff.workers.tasks import download_product_dataset_job

logger = get_logger()

settings.init_sentry(integrations=[FalconIntegration()])

TRANSLATION_STORE = TranslationStore()
TRANSLATION_STORE.load()


def get_server_type_from_req(
    req: falcon.Request, default: ServerType = ServerType.off
) -> ServerType:
    """Get `ServerType` value from POST x-www-form-urlencoded or GET
    requests."""
    media = req.get_media(default_when_empty=None)
    if media is not None and "server_type" in media:
        server_type_str = media["server_type"]
    else:
        server_type_str = req.get_param("server_type")

    if server_type_str is None:
        return default

    try:
        return ServerType[server_type_str]
    except KeyError:
        raise falcon.HTTPBadRequest(f"invalid `server_type`: {server_type_str}")


COUNTRY_NAME_TO_ENUM = {COUNTRY_CODE_TO_NAME[item]: item for item in Country}


def get_countries_from_req(req: falcon.Request) -> list[Country] | None:
    """Parse `countries` query string from request."""
    countries_str: list[str] | None = req.get_param_as_list("countries")
    if countries_str is None:
        return None

    # countries_str is a list of 2-letter country codes
    try:
        return [Country[country_str] for country_str in countries_str]
    except KeyError:
        raise falcon.HTTPBadRequest(
            description=f"invalid `countries` value: {countries_str}"
        )


def _get_skip_voted_on(auth: OFFAuthentication | None, device_id: str) -> SkipVotedOn:
    """Create a SkipVotedOn object based on request params.
    This object is used to determine if the user has already voted on the insight.

    If the user is not authenticated, the device_id (either an ID sent by the client or
    the IP address as fallback) is used.

    If the user is authenticated, the username is used.
    """
    if not auth:
        return SkipVotedOn(SkipVotedType.DEVICE_ID, device_id)

    username: str | None = auth.get_username()
    if not username:
        return SkipVotedOn(SkipVotedType.DEVICE_ID, device_id)

    return SkipVotedOn(SkipVotedType.USERNAME, username)


def normalize_req_barcode(barcode: str | None) -> str | None:
    """Normalize the `barcode` parameter provided in the Falcon request."""
    if not barcode:
        return None
    return normalize_barcode(barcode)


###########
# IMPORTANT: remember to update documentation at doc/references/api.yml if you
# change API
###########


class ProductInsightResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response, barcode: str):
        barcode = normalize_barcode(barcode)
        response: JSONType = {}
        server_type = get_server_type_from_req(req)
        insights = [
            insight.to_dict()
            for insight in get_insights(
                barcode=barcode, server_type=server_type, limit=None
            )
        ]

        if not insights:
            response["status"] = "no_insights"
        else:
            response["insights"] = insights
            response["status"] = "found"

        resp.media = response


class ProductInsightDetail:
    def on_get(self, req: falcon.Request, resp: falcon.Response, insight_id: uuid.UUID):
        try:
            insight: ProductInsight = ProductInsight.get_by_id(insight_id)
        except ProductInsight.DoesNotExist:
            raise falcon.HTTPNotFound()

        resp.media = insight.to_dict()


class InsightCollection:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        response: JSONType = {}
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        page: int = req.get_param_as_int("page", min_value=1, default=1)
        keep_types: list[str] | None = req.get_param_as_list(
            "insight_types", required=False
        )
        barcode: str | None = normalize_req_barcode(req.get_param("barcode"))
        annotated: bool | None = req.get_param_as_bool("annotated")
        annotation: int | None = req.get_param_as_int("annotation")
        value_tag: str = req.get_param("value_tag")
        brands = req.get_param_as_list("brands") or None
        predictor = req.get_param("predictor")
        server_type = get_server_type_from_req(req)
        countries: list[Country] | None = get_countries_from_req(req)
        order_by: str | None = req.get_param("order_by")
        campaigns: list[str] | None = req.get_param_as_list("campaigns") or None
        lc: list[str] | None = req.get_param_as_list("lc") or None

        if order_by not in ("random", "popularity", None):
            raise falcon.HTTPBadRequest(
                description=f"invalid `order_by` value: {order_by}"
            )

        if keep_types:
            # Limit the number of types to prevent slow SQL queries
            keep_types = keep_types[:10]

        if brands is not None:
            # Limit the number of brands to prevent slow SQL queries
            brands = brands[:10]

        device_id = device_id_from_request(req)
        auth: OFFAuthentication | None = parse_auth(req)
        avoid_voted_on = _get_skip_voted_on(auth, device_id)
        # Counting the number of insights that match the vote
        # criteria can be very costly, so we limit the count to 100
        max_count = 100
        get_insights_ = functools.partial(
            get_insights,
            server_type=server_type,
            keep_types=keep_types,
            countries=countries,
            value_tag=value_tag,
            brands=brands,
            annotated=annotated,
            annotation=annotation,
            barcode=barcode,
            predictor=predictor,
            order_by=order_by,
            campaigns=campaigns,
            avoid_voted_on=avoid_voted_on,
            max_count=max_count,
            lc=lc,
        )

        offset: int = (page - 1) * count
        insights = [i.to_dict() for i in get_insights_(limit=count, offset=offset)]
        response["count"] = get_insights_(count=True)

        if not insights:
            response["insights"] = []
            response["status"] = "no_insights"
        else:
            response["insights"] = insights
            response["status"] = "found"

        resp.media = response


class RandomInsightResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        response: JSONType = {}

        insight_type: str | None = req.get_param("type")
        value_tag: str | None = req.get_param("value_tag")
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        predictor = req.get_param("predictor")
        server_type = get_server_type_from_req(req)
        countries = get_countries_from_req(req)

        keep_types = [insight_type] if insight_type else None
        get_insights_ = functools.partial(
            get_insights,
            server_type=server_type,
            keep_types=keep_types,
            countries=countries,
            value_tag=value_tag,
            order_by="random",
            predictor=predictor,
        )

        insights = [insight.to_dict() for insight in get_insights_(limit=count)]
        response["count"] = get_insights_(count=True)

        if not insights:
            response["insights"] = []
            response["status"] = "no_insights"
        else:
            response["insights"] = insights
            response["status"] = "found"

        resp.media = response


def parse_auth(req: falcon.Request) -> OFFAuthentication | None:
    session_cookie = req.get_cookie_values("session")

    if session_cookie:
        session_cookie = session_cookie[0]

    authorization = req.get_header("Authorization")

    username = None
    password = None
    if authorization is not None:
        try:
            username, password = basic_decode(authorization)
        except BasicAuthDecodeError:
            raise falcon.HTTPUnauthorized(
                "Invalid authentication, Basic auth expected."
            )

    if not session_cookie and not username and not password:
        return None

    return OFFAuthentication(
        session_cookie=session_cookie, username=username, password=password
    )


def parse_valid_token(req: falcon.Request, ref_token_name: str) -> bool:
    """Parse and validate authentification token from request.

    :param req: Request.
    :type req: falcon.Request
    :param ref_token_name: Secret environment variable name.
    :type ref_token_name: str
    :return: Token valid or not.
    """
    auth_header = req.get_header("Authorization", required=True)

    try:
        scheme, token = auth_header.strip().split()
        if scheme.lower() != "bearer":
            raise falcon.HTTPUnauthorized(
                "Invalid authentication scheme: 'Bearer Token' expected."
            )
        is_token_valid = validate_token(token, ref_token_name)
        if not is_token_valid:
            raise falcon.HTTPUnauthorized("Invalid token.")
        else:
            return True
    except ValueError:
        raise falcon.HTTPUnauthorized("Invalid authentication scheme.")


def device_id_from_request(req: falcon.Request) -> str:
    """Returns the 'device_id' from the request parameters, or a hash of the
    access route (which should be the IPs of the proxies and the client)."""
    return req.get_param(
        "device_id",
        default=hashlib.sha1(
            str(req.access_route).encode(), usedforsecurity=False
        ).hexdigest(),
    )


class AnnotateInsightResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        insight_id = req.get_param_as_uuid("insight_id", required=True)
        annotation = req.get_param_as_int(
            "annotation", required=True, min_value=-1, max_value=2
        )

        update = req.get_param_as_bool("update", default=True)
        # This field is only needed for nutritional table structure insights.
        data: JSONType | None = req.get_param_as_json("data")

        if annotation == 2:
            if data is None:
                raise falcon.HTTPBadRequest(
                    description="`data` must be provided when annotation == 2"
                )
            if not update:
                raise falcon.HTTPBadRequest(
                    description="`update` must be true when annotation == 2"
                )

        if data is not None and annotation != 2:
            raise falcon.HTTPBadRequest(
                description="`annotation` must be 2 when `data` is provided"
            )

        auth = parse_auth(req)
        if auth is not None and auth.get_username() == "null":
            # Smoothie currently sends 'null' as username for anonymous voters
            auth = None

        trusted_annotator = auth is not None

        if not trusted_annotator and annotation == 2:
            raise falcon.HTTPBadRequest(
                description="`data` cannot be provided when the user is not authenticated"
            )

        device_id = device_id_from_request(req)
        logger.info(
            "New annotation received from %s (annotation: %s, insight: %s)",
            auth.get_username() if auth else "unknown annotator",
            annotation,
            insight_id,
        )

        annotation_result = save_annotation(
            insight_id,
            annotation,
            update=update,
            data=data,
            auth=auth,
            device_id=device_id,
            trusted_annotator=trusted_annotator,
        )

        resp.media = {
            "status_code": annotation_result.status_code,
            "status": annotation_result.status,
            "description": annotation_result.description,
        }


class NutritionPredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        image_url = req.get_param("image_url", required=True)
        ocr_url = req.get_param("ocr_url", required=True)

        image = typing.cast(
            Image.Image | None,
            get_image_from_url(
                image_url, error_raise=False, session=http_session, use_cache=False
            ),
        )

        if image is None:
            logger.info("Error while downloading image %s", image_url)
            resp.media = {
                "error": "download_error",
                "error_description": f"an error occurred while downloading image: {image_url}",
            }
            return

        ocr_result = OCRResult.from_url(ocr_url, http_session, error_raise=False)

        if ocr_result is None:
            logger.info("Error while downloading OCR JSON %s", ocr_url)
            resp.media = {
                "error": "download_error",
                "error_description": f"an error occurred while downloading OCR JSON: {ocr_url}",
            }
            return

        output = nutrition_extraction.predict(image, ocr_result)

        predictions = []
        if output is not None:
            prediction = {
                "nutrients": {
                    entity: dataclasses.asdict(nutrient)
                    for entity, nutrient in output.nutrients.items()
                },
                "entities": dataclasses.asdict(output.entities),
            }
            predictions.append(prediction)

        resp.media = {
            "predictions": predictions,
        }


def transform_to_prediction_type(value: str) -> PredictionType:
    """Function to transform string into `PredictionType`, compatible with
    falcon `req.get_param` function.

    Falcon expects a `ValueError` to be raised if the value is invalid.
    """
    try:
        return PredictionType[value]
    except KeyError:
        raise ValueError()


class OCRPredictionPredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        ocr_url = req.get_param("ocr_url", required=True)
        server_type = get_server_type_from_req(req)
        barcode = extract_barcode_from_url(ocr_url)
        prediction_types = req.get_param_as_list(
            "prediction_types",
            default=DEFAULT_OCR_PREDICTION_TYPES,
            transform=transform_to_prediction_type,
        )
        if barcode is None:
            raise falcon.HTTPBadRequest(f"invalid OCR URL: {ocr_url}")

        try:
            predictions = extract_ocr_predictions(
                ProductIdentifier(barcode, server_type),
                ocr_url,
                prediction_types,
            )

        except requests.exceptions.RequestException:
            resp.media = {
                "error": "download_error",
                "error_description": "an error occurred during OCR JSON download",
            }
            return

        except OCRParsingException as e:
            logger.error(e)
            resp.media = {
                "error": "invalid_ocr",
                "error_description": "an error occurred during OCR parsing",
            }
            return

        resp.media = {
            "predictions": predictions,
        }


class CategoryPredictorResource:
    @jsonschema.validate(schema.PREDICT_CATEGORY_SCHEMA)
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """Predict categories using neural categorizer and matching algorithm
        for a specific product."""
        server_type = get_server_type_from_req(req)

        if server_type != ServerType.off:
            raise falcon.HTTPBadRequest(
                f"category predictor is only available for 'off' server type (here: '{server_type.name}')"
            )

        media = req.get_media()
        neural_model_name = None
        if (neural_model_name_str := media.get("neural_model_name")) is not None:
            neural_model_name = NeuralCategoryClassifierModel[neural_model_name_str]

        if "barcode" in media:
            # Fetch product from DB
            barcode: str = normalize_barcode(media["barcode"])
            product = get_product(ProductIdentifier(barcode, server_type)) or {}
            if not product:
                raise falcon.HTTPNotFound(description=f"product {barcode} not found")
            product_id = ProductIdentifier(barcode, server_type)
        else:
            product = media["product"]
            product_id = ProductIdentifier("NULL", server_type)

            if (ingredient_tags := product.pop("ingredients_tags", None)) is not None:
                # Convert to a format recognized by `CategoryClassifier` class
                product["ingredients"] = [{"id": id_} for id_ in ingredient_tags]

        resp.media = predict_category(
            product,
            product_id,
            deepest_only=media.get("deepest_only", False),
            threshold=media.get("threshold"),
            neural_model_name=neural_model_name,
            clear_cache=True,  # clear resource cache to save memory
        )


class IngredientListPredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """Predict ingredient list using ingredient NER model from an OCR
        URL.

        This endpoint is *experimental* and shouldn't be used in production
        settings.
        """
        server_type = get_server_type_from_req(req)

        if server_type != ServerType.off:
            raise falcon.HTTPBadRequest(
                f"ingredient list predictor is only available for 'off' server type (here: '{server_type.name}')"
            )

        ocr_url = req.get_param("ocr_url", required=True)
        try:
            ocr_result = OCRResult.from_url(ocr_url, http_session, error_raise=True)
        except OCRResultGenerationException as e:
            error_message, _ = e.args
            resp.media = {
                "error": "ocr_input_error",
                "description": error_message,
            }
            return

        ocr_result = cast(OCRResult, ocr_result)
        aggregation_strategy = req.get_param("aggregation_strategy", default="FIRST")
        model_version = req.get_param("model_version", default="1")
        output = ingredient_list.predict_from_ocr(
            ocr_result,
            aggregation_strategy=ingredient_list.AggregationStrategy[
                aggregation_strategy
            ],
            model_version=model_version,
        )
        resp.media = dataclasses.asdict(output)


class LanguagePredictorResource:
    def _on_get_post(self, req: falcon.Request, resp: falcon.Response):
        """Predict language of a text.

        This method is used by both GET and POST endpoints.
        """
        params = validate_params(
            {
                "text": req.get_param("text"),
                "k": req.get_param("k"),
                "threshold": req.get_param("threshold"),
            },
            schema.LanguagePredictorResourceParams,
        )
        params = cast(schema.LanguagePredictorResourceParams, params)
        language_predictions = predict_lang(params.text, params.k, params.threshold)
        resp.media = {
            "predictions": [
                dataclasses.asdict(prediction) for prediction in language_predictions
            ]
        }

    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """Predict language of a text."""
        self._on_get_post(req, resp)

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """Predict language of a text.

        For long text, use POST instead of GET, as the length of the query
        string is limited.
        """
        self._on_get_post(req, resp)


class ProductLanguagePredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """Predict the languages displayed on the product images, using
        `image_lang` predictions as input."""
        barcode = normalize_barcode(req.get_param("barcode", required=True))
        server_type = get_server_type_from_req(req)
        counts: dict[str, int] = defaultdict(int)
        image_ids: list[int] = []

        for prediction_data, source_image in (
            Prediction.select(Prediction.data, Prediction.source_image)
            .where(
                Prediction.barcode == barcode,
                Prediction.server_type == server_type.name,
                Prediction.type == PredictionType.image_lang.name,
            )
            .tuples()
            .iterator()
        ):
            image_ids.append(int(Path(source_image).stem))
            for lang, lang_count in prediction_data["count"].items():
                counts[lang] += lang_count

        words_n = counts.pop("words")
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        counts_list = [{"count": count, "lang": lang} for lang, count in sorted_counts]
        percent_list = [
            {"percent": (count * 100 / words_n), "lang": lang}
            for lang, count in sorted_counts
        ]
        resp.media = {
            "counts": counts_list,
            "percent": percent_list,
            "image_ids": sorted(image_ids),
        }


class UpdateDatasetResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """Re-import the Product Opener product dump."""

        enqueue_job(
            download_product_dataset_job, queue=low_queue, job_kwargs={"timeout": "1h"}
        )

        resp.media = {
            "status": "scheduled",
        }

    def on_get(self, req: falcon.Request, resp: falcon.Response):
        resp.media = {
            "etag": get_product_dataset_etag(),
        }


class ImageCropResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        image_url = req.get_param("image_url", required=True)
        y_min = req.get_param_as_float("y_min", required=True)
        x_min = req.get_param_as_float("x_min", required=True)
        y_max = req.get_param_as_float("y_max", required=True)
        x_max = req.get_param_as_float("x_max", required=True)

        parsed_img_url = urllib.parse.urlparse(image_url)
        if parsed_img_url.hostname not in settings.CROP_ALLOWED_DOMAINS:
            raise falcon.HTTPBadRequest("Domain not allowed!")

        # Get image from cache, as Hunger Games can requests many crops
        # from the same image
        image = typing.cast(
            Image.Image | None,
            get_image_from_url(
                image_url, session=http_session, error_raise=False, use_cache=True
            ),
        )

        if image is None:
            raise falcon.HTTPBadRequest(f"Could not fetch image: {image_url}")

        (left, right, top, bottom) = (
            x_min * image.width,
            x_max * image.width,
            y_min * image.height,
            y_max * image.height,
        )
        cropped_image = image.crop((left, top, right, bottom))
        image_response(cropped_image, resp)


class ImagePredictionImporterResource:
    @jsonschema.validate(schema.IMAGE_PREDICTION_IMPORTER_SCHEMA)
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        server_type = get_server_type_from_req(req)
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        inserts = []
        media = req.get_media()

        for prediction in media["predictions"]:
            product_id = ProductIdentifier(prediction["barcode"], server_type)
            source_image = generate_image_path(product_id, prediction.pop("image_id"))
            inserts.append(
                {
                    "timestamp": timestamp,
                    "source_image": source_image,
                    **prediction,
                }
            )

        inserted = batch_insert(ImagePrediction, inserts)
        logger.info("%s image predictions inserted", inserted)


class ImagePredictionResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        page: int = req.get_param_as_int("page", min_value=1, default=1)
        with_logo: bool | None = req.get_param_as_bool("with_logo", default=None)
        model_name: str | None = req.get_param("model_name")
        type_: str | None = req.get_param("type")
        model_version: str | None = req.get_param("model_version")
        barcode: str | None = normalize_req_barcode(req.get_param("barcode"))
        image_id: str | None = req.get_param("image_id")
        min_confidence: float | None = req.get_param_as_float("min_confidence")
        server_type = get_server_type_from_req(req)

        get_image_predictions_ = functools.partial(
            get_image_predictions,
            with_logo=with_logo,
            barcode=barcode,
            image_id=image_id,
            type=type_,
            server_type=server_type,
            model_name=model_name,
            model_version=model_version,
            min_confidence=min_confidence,
        )

        offset: int = (page - 1) * count
        image_predictions = [
            i.to_dict() for i in get_image_predictions_(limit=count, offset=offset)
        ]
        response: JSONType = {"count": get_image_predictions_(count=True)}

        if not image_predictions:
            response["image_predictions"] = []
            response["status"] = "no_image_predictions"
        else:
            response["image_predictions"] = image_predictions
            response["status"] = "found"

        resp.media = response


class ImagePredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        image_url = req.get_param("image_url", required=True)
        models: list[str] = req.get_param_as_list("models", required=True)
        threshold: float = req.get_param_as_float("threshold", default=0.5)
        mode: str = req.get_param("mode", default="PIL")
        nms_threshold: float | None = req.get_param_as_float(
            "nms_threshold", default=None
        )
        nms_eta: float | None = req.get_param_as_float("nms_eta", default=None)

        if mode not in ("PIL", "np"):
            raise falcon.HTTPBadRequest(
                "invalid_mode", "mode must be either 'PIL' or 'np'"
            )
        mode = typing.cast(Literal["PIL", "np"], mode)

        available_object_detection_models = list(
            ObjectDetectionModel.__members__.keys()
        )
        available_clf_models = list(ImageClassificationModel.__members__.keys())
        available_models = available_object_detection_models + available_clf_models

        for model_name in models:
            if model_name not in available_models:
                raise falcon.HTTPBadRequest(
                    "invalid_model",
                    f"unknown model {model_name}, available models: {', '.join(available_models)}",
                )

        output_image = req.get_param_as_bool("output_image")

        if output_image is None:
            output_image = False

        if output_image:
            if len(models) != 1:
                raise falcon.HTTPBadRequest(
                    "invalid_request",
                    "a single model must be specified with the `models` parameter "
                    "when `output_image` is True",
                )
            if models[0] not in available_object_detection_models:
                raise falcon.HTTPBadRequest(
                    "invalid_request",
                    f"model {models[0]} does not support image output",
                )

        image = typing.cast(
            Image.Image | None,
            get_image_from_url(
                image_url,
                session=http_session,
                error_raise=False,
                use_cache=True,
                return_type=mode,
            ),
        )

        if image is None:
            raise falcon.HTTPBadRequest(f"Could not fetch image: {image_url}")

        predictions = {}

        for model_name in models:
            if model_name in available_object_detection_models:
                model = ObjectDetectionModelRegistry.get(
                    ObjectDetectionModel[model_name]
                )
                result = model.detect_from_image(
                    image,
                    output_image=output_image,
                    threshold=threshold,
                    nms_threshold=nms_threshold,
                    nms_eta=nms_eta,
                )

                if output_image:
                    boxed_image = cast(Image.Image, result.boxed_image)
                    image_response(boxed_image, resp)
                    return
                else:
                    predictions[model_name] = result.to_list()
            else:
                model_enum = ImageClassificationModel[model_name]
                classifier = image_classifier.ImageClassifier(
                    image_classifier.MODELS_CONFIG[model_enum]
                )
                predictions[model_name] = [
                    {"label": label, "score": score}
                    for label, score in classifier.predict(image)
                ]

        resp.media = {"predictions": predictions}


def image_response(image: Image.Image, resp: falcon.Response) -> None:
    resp.content_type = "image/jpeg"
    fp = io.BytesIO()
    # JPEG doesn't support RGBA, so we convert to RGB if needed
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(fp, "JPEG")
    stream_len = fp.tell()
    fp.seek(0)
    resp.set_stream(fp, stream_len)


class ImageLogoResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """Return details about requested logos."""
        logo_ids: list[str] = req.get_param_as_list(
            "logo_ids", transform=int, required=True
        )

        if len(logo_ids) > 500:
            raise falcon.HTTPBadRequest(
                description="too many logos requested, max: 500"
            )

        logos = []
        for logo in (
            LogoAnnotation.select()
            .join(ImagePrediction)
            .join(ImageModel)
            .where(
                LogoAnnotation.id.in_(logo_ids),
                # Don't include logos from deleted images
                ImageModel.deleted == False,  # noqa
            )  # noqa
            .iterator()
        ):
            logo_dict = logo.to_dict()
            image_prediction = logo_dict.pop("image_prediction")
            logo_dict["image"] = image_prediction["image"]
            logos.append(logo_dict)

        resp.media = {"logos": logos, "count": len(logos)}


class ImageLogoSearchResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        server_type = get_server_type_from_req(req)
        count: int = req.get_param_as_int(
            "count", min_value=1, max_value=2000, default=25
        )
        type_: str | None = req.get_param("type")
        barcode: str | None = normalize_req_barcode(req.get_param("barcode"))
        value: str | None = req.get_param("value")
        taxonomy_value: str | None = req.get_param("taxonomy_value")
        min_confidence: float | None = req.get_param_as_float("min_confidence")
        random: bool = req.get_param_as_bool("random", default=False)
        annotated: bool | None = req.get_param_as_bool("annotated")

        if type_ is None and (value is not None or taxonomy_value is not None):
            raise falcon.HTTPBadRequest(
                description="a type is required if `value` or `taxonomy_value` is provided"
            )

        if value is not None and taxonomy_value is not None:
            raise falcon.HTTPBadRequest(
                description="`value` and `taxonomy_value` are mutually exclusive parameters"
            )

        if type_ == "label" and taxonomy_value is None and value is not None:
            raise falcon.HTTPBadRequest(
                description="you should provide a `taxonomy_value` and not a `value` "
                "for label type"
            )

        where_clauses = [
            ImageModel.server_type == server_type.name,
            # Don't include logos from deleted images
            ImageModel.deleted == False,  # noqa
        ]
        if annotated is not None:
            where_clauses.append(LogoAnnotation.annotation_value.is_null(not annotated))

        if min_confidence is not None:
            where_clauses.append(LogoAnnotation.score >= min_confidence)

        if barcode is not None:
            where_clauses.append(ImageModel.barcode == barcode)

        if type_ is not None:
            where_clauses.append(LogoAnnotation.annotation_type == type_)

        if value is not None:
            value_tag = get_tag(value)
            where_clauses.append(LogoAnnotation.annotation_value_tag == value_tag)

        if taxonomy_value is not None:
            where_clauses.append(LogoAnnotation.taxonomy_value == taxonomy_value)

        query = LogoAnnotation.select()
        query = query.join(ImagePrediction).join(ImageModel)

        if where_clauses:
            query = query.where(*where_clauses)

        query_count = query.count()

        if random:
            query = query.order_by(peewee.fn.Random())

        query = query.limit(count)
        items = [item.to_dict() for item in query.iterator()]

        for item in items:
            image_prediction = item.pop("image_prediction")
            item["image"] = image_prediction["image"]

        resp.media = {"logos": items, "count": query_count}


def check_logo_annotation(type_: str, value: str | None = None) -> None:
    """Check if the log annotation type and value are valid, and raise an
    exception if not.

    :param type_: the annotation type (brand, category, label, store)
    :param value: the annotation value, if any
    :raises falcon.HTTPBadRequest: if the annotation type or value is invalid
    """
    if value is not None:
        if type_ == "label" and not is_prefixed_value(value):
            raise falcon.HTTPBadRequest(
                description=f"language-prefixed value are required for label type (here: {value})"
            )
    elif type_ in ("brand", "category", "label", "store"):
        raise falcon.HTTPBadRequest(description=f"value required for type {type_})")


class ImageLogoDetailResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response, logo_id: int):
        logo = LogoAnnotation.get_or_none(id=logo_id)

        if logo is None:
            resp.status = falcon.HTTP_404
            return

        logo_dict = logo.to_dict()
        image_prediction = logo_dict.pop("image_prediction")
        logo_dict["image"] = image_prediction["image"]
        resp.media = logo_dict

    @jsonschema.validate(schema.UPDATE_LOGO_SCHEMA)
    def on_put(self, req: falcon.Request, resp: falcon.Response, logo_id: int):
        auth = parse_auth(req)
        logger.info(
            "Received logo annotation update request for logo %s (user: %s)",
            logo_id,
            auth.get_username() if auth else "unknown",
        )
        media = req.get_media()
        if auth is None:
            raise falcon.HTTPForbidden(
                description="authentication is required to annotate logos"
            )

        with db.atomic():
            logo: LogoAnnotation | None = LogoAnnotation.get_or_none(id=logo_id)
            if logo is None:
                resp.status = falcon.HTTP_404
                return

            type_ = media["type"]
            value = media.get("value") or None
            check_logo_annotation(type_, value)

            if type_ != logo.annotation_type or value != logo.annotation_value:
                annotated_logos = update_logo_annotations(
                    [(type_, value, logo)],
                    username=auth.get_username() or "unknown",
                    completed_at=datetime.datetime.now(datetime.timezone.utc),
                )
                server_type = ServerType[logo.image_prediction.image.server_type]
                generate_insights_from_annotated_logos(
                    annotated_logos, auth, server_type
                )

        resp.status = falcon.HTTP_204


class ImageLogoResetResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response, logo_id: int):
        with db.atomic():
            logo = LogoAnnotation.get_or_none(id=logo_id)
            if logo is None:
                resp.status = falcon.HTTP_404
                return

            annotation_type = logo.annotation_type
            logo.annotation_value = None
            logo.annotation_value_tag = None
            logo.taxonomy_value = None
            logo.annotation_type = None
            logo.username = None
            logo.completed_at = None
            logo.save()

            if annotation_type in ("brand", "label"):
                prediction_deleted = (
                    Prediction.delete()
                    .where(
                        # Speed-up filtering by providing additional filters
                        Prediction.barcode == logo.barcode,
                        Prediction.type == annotation_type,
                        Prediction.predictor == "universal-logo-detector",
                        Prediction.data["logo_id"] == str(logo.id),
                    )
                    .execute()
                )
                insights_deleted = (
                    ProductInsight.delete()
                    .where(
                        # Speed-up filtering by providing additional filters
                        ProductInsight.barcode == logo.barcode,
                        ProductInsight.type == annotation_type,
                        # never delete annotated insights
                        ProductInsight.annotation.is_null(),
                        ProductInsight.predictor == "universal-logo-detector",
                        # We don't have an index on data, but the number of
                        # rows should be small enough to not be a problem
                        ProductInsight.data["logo_id"] == str(logo_id),
                    )
                    .execute()
                )
                logger.info(
                    "prediction deleted: %s, insight deleted: %s",
                    prediction_deleted,
                    insights_deleted,
                )

        resp.status = falcon.HTTP_204


class ImageLogoAnnotateResource:
    @jsonschema.validate(schema.ANNOTATE_LOGO_SCHEMA)
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        auth = parse_auth(req)
        media = req.get_media()
        if auth is None:
            raise falcon.HTTPForbidden(
                description="authentication is required to annotate logos"
            )
        server_type = get_server_type_from_req(req)
        annotations = media["annotations"]
        completed_at = datetime.datetime.now(datetime.timezone.utc)
        annotation_logos = []

        with db.atomic():
            for annotation in annotations:
                logo_id = annotation["logo_id"]
                type_ = annotation["type"]
                value = annotation["value"] or None
                check_logo_annotation(type_, value)

                try:
                    logo = LogoAnnotation.get_by_id(logo_id)
                except LogoAnnotation.DoesNotExist:
                    raise falcon.HTTPNotFound(description=f"logo {logo_id} not found")

                if logo.annotation_type is None:
                    # Don't annotate already annotated logos
                    annotation_logos.append((type_, value, logo))

            if annotation_logos:
                annotated_logos = update_logo_annotations(
                    annotation_logos,
                    username=auth.get_username() or "unknown",
                    completed_at=completed_at,
                )
            else:
                annotated_logos = []

        if annotated_logos:
            logo_ids = [logo.id for logo in annotated_logos]
            enqueue_job(
                generate_insights_from_annotated_logos_job,
                # we have logo IDs of different products, so we don't send the
                # job to a product-specific queue
                get_high_queue(),
                {"result_ttl": 0, "timeout": "5m"},
                logo_ids=logo_ids,
                server_type=server_type,
                auth=auth,
            )
        resp.media = {"annotated": len(annotated_logos)}


class ImageLogoUpdateResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """Bulk update logo annotations: change type and value of logos that
        have specific types and values.

        Because this endpoint mass-update annotations, leave it out of API
        documentation.
        """
        source_value = req.get_param("source_value", required=True)
        source_type = req.get_param("source_type", required=True)
        target_value = req.get_param("target_value", required=True)
        target_type = req.get_param("target_type", required=True)

        auth = parse_auth(req)
        username = None if auth is None else auth.get_username()
        completed_at = datetime.datetime.now(datetime.timezone.utc)

        target_value_tag = get_tag(target_value)
        source_value_tag = get_tag(source_value)
        taxonomy_value = match_taxonomized_value(target_value_tag, target_type)

        query = LogoAnnotation.update(
            {
                LogoAnnotation.annotation_type: target_type,
                LogoAnnotation.annotation_value: target_value,
                LogoAnnotation.annotation_value_tag: target_value_tag,
                LogoAnnotation.taxonomy_value: taxonomy_value,
                LogoAnnotation.username: username,
                LogoAnnotation.completed_at: completed_at,
            }
        ).where(
            LogoAnnotation.annotation_type == source_type,
            LogoAnnotation.annotation_value_tag == source_value_tag,
        )
        updated = query.execute()
        resp.media = {"updated": updated}


class ANNResource:
    def on_get(
        self, req: falcon.Request, resp: falcon.Response, logo_id: int | None = None
    ):
        """Search for nearest neighbors of:
        - a random logo (if logo_id not provided)
        - a specific logo otherwise
        """
        count = req.get_param_as_int("count", min_value=1, max_value=500, default=100)
        server_type = get_server_type_from_req(req)
        es_client = get_es_client()

        if logo_id is None:
            # To fetch a random logo that has an embedding, we use
            # TABLESAMPLE SYSTEM. The parameter in parentheses is the
            # percentage of rows to sample.
            # Here, we sample 20% of the rows in the logo_embedding table.
            # See https://www.postgresql.org/docs/current/sql-select.html
            # for more information.
            result = db.execute_sql(
                """
                SELECT logo_id, embedding
                FROM embedding.logo_embedding as t1 TABLESAMPLE SYSTEM (20)
                JOIN logo_annotation AS t2 ON t1.logo_id = t2.id
                WHERE t2.server_type = %s
                LIMIT 1;
                """,
                (server_type.name,),
            ).fetchone()

            if not result:
                resp.media = {"results": [], "count": 0, "query_logo_id": None}
                return

            logo_id, embedding = result
        else:
            logo_embedding = LogoEmbedding.get_or_none(logo_id=logo_id)

            if logo_embedding is None:
                resp.status = falcon.HTTP_404
                return
            embedding = logo_embedding.embedding

        raw_results = [
            item
            for item in knn_search(es_client, embedding, count, server_type=server_type)
            if item[0] != logo_id
        ][:count]
        results = [{"logo_id": item[0], "distance": item[1]} for item in raw_results]
        resp.media = {
            "results": results,
            "count": len(results),
            "query_logo_id": logo_id,
        }


SERVER_DOMAIN_REGEX = re.compile(
    r"api(\.pro)?\.open(food|beauty|product|petfood)facts\.(org|net)"
)


def check_server_domain(server_domain: str):
    if not SERVER_DOMAIN_REGEX.fullmatch(server_domain):
        raise falcon.HTTPBadRequest(f"invalid `server_domain`: {server_domain}")

    tld = server_domain.rsplit(".", maxsplit=1)[-1]
    instance_tld = settings._get_tld()
    if tld != instance_tld:
        raise falcon.HTTPBadRequest(
            f"invalid `server_domain`, expected '{instance_tld}' tld, got '{tld}'"
        )


def question_insight_type_sort_func(insight: ProductInsight) -> int:
    """Function to sort questions on a specific product by priority.

    Some questions are more important than others, so we want them to be
    displayed first. The order is the following:

    - category
    - label
    - brand
    - remaining questions

    :param insight: The product insight
    :return: a sorting key, lower has more priority
    """
    if insight.type == InsightType.category.name:
        return 0
    if insight.type == InsightType.label.name:
        return 1
    elif insight.type == InsightType.brand.name:
        return 2
    return 3


class ProductQuestionsResource:
    """Get questions about a product to confirm/infirm an insight

    see also doc/explanation/questions.md
    """

    def on_get(self, req: falcon.Request, resp: falcon.Response, barcode: str):
        barcode = normalize_barcode(barcode)
        response: JSONType = {}
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        lang: str = req.get_param("lang", default="en")
        server_type = get_server_type_from_req(req)
        # If the device_id is not provided as a request parameter, we use the
        # hash of the IPs as a backup.
        device_id = device_id_from_request(req)

        auth: OFFAuthentication | None = parse_auth(req)

        keep_types: list[str] | None = req.get_param_as_list(
            "insight_types", required=False
        )
        keep_types = filter_question_insight_types(keep_types)

        insights = sorted(
            get_insights(
                barcode=barcode,
                server_type=server_type,
                keep_types=keep_types,
                limit=count,
                order_by="n_votes",
                avoid_voted_on=_get_skip_voted_on(auth, device_id),
                automatically_processable=False,
            ),
            key=question_insight_type_sort_func,
        )

        if not insights:
            response["questions"] = []
            response["status"] = "no_questions"
        else:
            questions: list[JSONType] = []

            for insight in insights:
                formatter_cls = QuestionFormatterFactory.get(insight.type)
                formatter: QuestionFormatter = formatter_cls(TRANSLATION_STORE)
                question = formatter.format_question(insight, lang)
                questions.append(question.serialize())

            response["questions"] = questions
            response["status"] = "found"

        resp.media = response


class RandomQuestionsResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        get_questions_resource_on_get(req, resp, "random")


class PopularQuestionsResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        get_questions_resource_on_get(req, resp, "popularity")


class QuestionsCollectionResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        order_by = req.get_param("order_by", default="popularity")

        if order_by not in ("random", "popularity", "confidence"):
            raise falcon.HTTPBadRequest(
                description=f"invalid '{order_by}' value for `order_by` parameter"
            )
        get_questions_resource_on_get(req, resp, order_by)


def get_questions_resource_on_get(
    req: falcon.Request,
    resp: falcon.Response,
    order_by: Literal["random", "popularity", "confidence"],
):
    response: JSONType = {}
    page: int = req.get_param_as_int("page", min_value=1, default=1)
    count: int = req.get_param_as_int("count", min_value=1, default=25)
    lang: str = req.get_param("lang", default="en")
    keep_types: list[str] | None = req.get_param_as_list(
        "insight_types", required=False
    )
    keep_types = filter_question_insight_types(keep_types)
    value_tag: str = req.get_param("value_tag")
    brands = req.get_param_as_list("brands") or None
    reserved_barcode: bool | None = req.get_param_as_bool(
        "reserved_barcode", default=False
    )
    server_type = get_server_type_from_req(req)
    countries = get_countries_from_req(req)
    # filter by annotation campaigns
    campaigns: list[str] | None = req.get_param_as_list("campaigns") or None
    with_image: bool | None = req.get_param_as_bool(
        "with_image", default=False
    )

    if campaigns is None:
        # `campaign` is a deprecated field, use campaigns now instead
        campaign: str | None = req.get_param("campaign")
        campaigns = [campaign] if campaign is not None else None

    predictor = req.get_param("predictor")

    # If the device_id is not provided as a request parameter, we use the
    # hash of the IPs as a backup.
    device_id = device_id_from_request(req)

    auth: OFFAuthentication | None = parse_auth(req)

    if reserved_barcode:
        # Include all results, including non reserved barcodes
        reserved_barcode = None

    if brands is not None:
        # Limit the number of brands to prevent slow SQL queries
        brands = brands[:10]

    avoid_voted_on = _get_skip_voted_on(auth, device_id)
    # Counting the number of insights that match the vote
    # criteria can be very costly, so we limit the count to 100
    max_count = 100
    get_insights_ = functools.partial(
        get_insights,
        server_type=server_type,
        keep_types=keep_types,
        countries=countries,
        value_tag=value_tag,
        brands=brands,
        order_by=order_by,
        reserved_barcode=reserved_barcode,
        avoid_voted_on=avoid_voted_on,
        max_count=max_count,
        automatically_processable=False,
        campaigns=campaigns,
        predictor=predictor,
        with_image=with_image,
    )

    offset: int = (page - 1) * count
    insights = list(get_insights_(limit=count, offset=offset))
    response["count"] = get_insights_(count=True)
    # This code should be merged with the one in ProductQuestionsResource.get
    if not insights:
        response["questions"] = []
        response["status"] = "no_questions"
    else:
        questions: list[JSONType] = []

        for insight in insights:
            formatter_cls = QuestionFormatterFactory.get(insight.type)

            if formatter_cls is None:
                continue

            formatter: QuestionFormatter = formatter_cls(TRANSLATION_STORE)
            question = formatter.format_question(insight, lang)
            questions.append(question.serialize())

        response["questions"] = questions
        response["status"] = "found"

    resp.media = response


class StatusResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        resp.media = {
            "status": "running",
        }


class HealthResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        from robotoff.health import health

        message, status, headers = health.run()
        resp.media = {
            "message": orjson.loads(message),
            "status": status,
            "headers": headers,
        }
        resp.status = str(status)


class DumpResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        keep_types: list[str] = req.get_param_as_list(
            "insight_types", required=False, default=[]
        )[:10]
        barcode = normalize_req_barcode(req.get_param("barcode"))
        annotated = req.get_param_as_bool("annotated", blank_as_true=False)
        value_tag = req.get_param("value_tag")
        count = req.get_param_as_int("count", min_value=0, max_value=10_000)
        server_type = get_server_type_from_req(req)

        get_insights_ = functools.partial(
            get_insights,
            server_type=server_type,
            barcode=barcode,
            keep_types=keep_types,
            annotated=annotated,
            value_tag=value_tag,
        )
        insight_count: int = get_insights_(count=True)  # type: ignore
        if insight_count > 10_000 and count is None:
            raise falcon.HTTPBadRequest(
                description=f"more than 10 000 insights matching criteria (here: {insight_count}), "
                "use more specific criteria or use count parameter"
            )

        insights_iter = get_insights_(limit=count, as_dict=True)
        writer = None

        with tempfile.TemporaryFile("w+", newline="") as temp_f:
            for insight_dict in insights_iter:
                serial = orjson.loads(orjson.dumps(insight_dict))

                if writer is None:
                    writer = csv.DictWriter(temp_f, fieldnames=serial.keys())
                    writer.writeheader()

                writer.writerow(serial)

            temp_f.seek(0)
            content = temp_f.read()

        if content:
            resp.content_type = "text/csv"
            resp.body = content
        else:
            resp.status = falcon.HTTP_204


class UserStatisticsResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response, username: str):
        annotation_count = (
            ProductInsight.select().where(ProductInsight.username == username).count()
        )
        resp.media = {"count": {"annotations": annotation_count}}


class ImageCollection:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        response: JSONType = {}
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        page: int = req.get_param_as_int("page", min_value=1, default=1)
        with_predictions: bool | None = req.get_param_as_bool(
            "with_predictions", default=False
        )
        barcode: str | None = normalize_req_barcode(req.get_param("barcode"))
        server_type = get_server_type_from_req(req)

        get_images_ = functools.partial(
            get_images,
            with_predictions=with_predictions,
            barcode=barcode,
            server_type=server_type,
        )

        offset: int = (page - 1) * count
        images = [i.to_dict() for i in get_images_(limit=count, offset=offset)]
        response["count"] = get_images_(count=True)

        if not images:
            response["images"] = []
            response["status"] = "no_images"
        else:
            response["images"] = images
            response["status"] = "found"

        resp.media = response


class PredictionCollection:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        page: int = req.get_param_as_int("page", min_value=1, default=1)
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        barcode: str | None = normalize_req_barcode(req.get_param("barcode"))
        value_tag: str = req.get_param("value_tag")
        keep_types: list[str] | None = req.get_param_as_list("types", required=False)
        server_type = get_server_type_from_req(req)

        if keep_types:
            # Limit the number of types to prevent slow SQL queries
            keep_types = keep_types[:10]

        get_predictions_ = functools.partial(
            get_predictions,
            keep_types=keep_types,
            value_tag=value_tag,
            barcode=barcode,
            server_type=server_type,
        )

        offset: int = (page - 1) * count
        predictions = [
            i.to_dict() for i in get_predictions_(limit=count, offset=offset)
        ]

        response: JSONType = {"count": get_predictions_(count=True)}

        if not predictions:
            response["predictions"] = []
            response["status"] = "no_predictions"
        else:
            response["predictions"] = list(predictions)
            response["status"] = "found"

        resp.media = response


class UnansweredQuestionCollection:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        response: JSONType = {}
        page: int = req.get_param_as_int("page", min_value=1, default=1)
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        insight_type: str = req.get_param("type")
        countries = get_countries_from_req(req)
        reserved_barcode: bool | None = req.get_param_as_bool(
            "reserved_barcode", default=False
        )
        server_type = get_server_type_from_req(req)
        # filter by annotation campaigns
        campaigns: list[str] | None = req.get_param_as_list("campaigns") or None
        if campaigns is None:
            # `campaign` is a deprecated field, use campaigns now instead
            campaign: str | None = req.get_param("campaign")
            campaigns = [campaign] if campaign is not None else None

        predictor = req.get_param("predictor")

        get_insights_ = functools.partial(
            get_insights,
            server_type=server_type,
            keep_types=[insight_type] if insight_type else None,
            group_by_value_tag=True,
            limit=count,
            countries=countries,
            automatically_processable=False,
            reserved_barcode=reserved_barcode,
            campaigns=campaigns,
            predictor=predictor,
        )

        offset: int = (page - 1) * count
        insights = list(get_insights_(offset=offset))

        response["count"] = get_insights_(count=True)

        if not insights:
            response["questions"] = []
            response["status"] = "no_questions"
        else:
            response["questions"] = insights
            response["status"] = "found"

        resp.media = response


class ImagePredictionCollection:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        response: JSONType = {}
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        page: int = req.get_param_as_int("page", min_value=1, default=1)
        with_logo: bool | None = req.get_param_as_bool("with_logo", default=False)
        barcode: str | None = normalize_req_barcode(req.get_param("barcode"))
        type: str | None = req.get_param("type")
        server_type = get_server_type_from_req(req)

        query_parameters = {
            "with_logo": with_logo,
            "barcode": barcode,
            "type": type,
            "server_type": server_type,
        }

        get_image_predictions_ = functools.partial(
            get_image_predictions, **query_parameters
        )

        offset: int = (page - 1) * count
        image_predictions = [
            i.to_dict() for i in get_image_predictions_(limit=count, offset=offset)
        ]
        response["count"] = get_image_predictions_(count=True)

        if not image_predictions:
            response["image_predictions"] = []
            response["status"] = "no_image_predictions"
        else:
            response["image_predictions"] = image_predictions
            response["status"] = "found"

        resp.media = response


class LogoAnnotationCollection:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        response: JSONType = {}
        barcode: str | None = normalize_req_barcode(req.get_param("barcode"))
        server_type = get_server_type_from_req(req)
        keep_types: list[str] | None = req.get_param_as_list("types", required=False)
        value_tag: str = req.get_param("value_tag")
        page: int = req.get_param_as_int("page", min_value=1, default=1)
        count: int = req.get_param_as_int("count", min_value=1, default=25)

        if keep_types:
            # Limit the number of types to prevent slow SQL queries
            keep_types = keep_types[:10]

        query_parameters = {
            "barcode": barcode,
            "keep_types": keep_types,
            "value_tag": value_tag,
            "server_type": server_type,
        }

        get_annotation_ = functools.partial(get_logo_annotation, **query_parameters)

        offset: int = (page - 1) * count
        annotation = [i.to_dict() for i in get_annotation_(limit=count, offset=offset)]
        response["count"] = get_annotation_(count=True)

        if not annotation:
            response["annotation"] = []
            response["status"] = "no_annotation"
        else:
            response["annotation"] = annotation
            response["status"] = "found"

        resp.media = response


class BatchJobImportResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        job_type_str: str = req.get_param("job_type", required=True)
        batch_dir: str = req.get_param("batch_dir", required=True)

        try:
            job_type = BatchJobType[job_type_str]
        except KeyError:
            raise falcon.HTTPBadRequest(
                description=f"invalid job_type: {job_type_str}. Valid job_types are: {[elt.value for elt in BatchJobType]}"
            )
        # We secure the endpoint.
        if parse_valid_token(req, "batch_job_key"):
            enqueue_job(
                import_batch_predictions,
                job_type=job_type,
                batch_dir=batch_dir,
                queue=low_queue,
                job_kwargs={"timeout": "8h"},
            )
        logger.info("Batch import %s has been queued.", job_type)

        resp.media = {"status": "Request successful. Importing processed data."}
        resp.status = falcon.HTTP_200


class RobotsTxtResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        # Disallow completely indexation: otherwise web crawlers send millions
        # of requests to Robotoff (420k requests/day by Google alone)
        resp.body = "User-agent: *\nDisallow: /\n"
        resp.content_type = falcon.MEDIA_TEXT
        resp.status = falcon.HTTP_200


def custom_handle_uncaught_exception(
    req: falcon.Request, resp: falcon.Response, ex: Exception, params
):
    """Handle uncaught exceptions and log them. Return a 500 error to the
    client."""
    raise falcon.HTTPInternalServerError(description=str(ex))


api = falcon.App(
    middleware=[
        falcon.CORSMiddleware(allow_origins="*", allow_credentials="*"),
        DBConnectionMiddleware(),
        # Clear cache after the request, to keep RAM usage low
        CacheClearMiddleware(),
    ],
)

json_handler = falcon.media.JSONHandler(dumps=orjson.dumps, loads=orjson.loads)
extra_handlers = {
    "application/json": json_handler,
}

api.req_options.media_handlers.update(extra_handlers)
api.resp_options.media_handlers.update(extra_handlers)

# Parse form parameters
api.req_options.auto_parse_form_urlencoded = True
api.req_options.strip_url_path_trailing_slash = True
api.req_options.auto_parse_qs_csv = True
# defines urls
api.add_route("/api/v1/insights/{barcode}", ProductInsightResource())
api.add_route("/api/v1/insights/detail/{insight_id:uuid}", ProductInsightDetail())
api.add_route("/api/v1/insights", InsightCollection())
api.add_route("/api/v1/insights/random", RandomInsightResource())
api.add_route("/api/v1/insights/annotate", AnnotateInsightResource())
api.add_route("/api/v1/insights/dump", DumpResource())
api.add_route("/api/v1/predict/nutrition", NutritionPredictorResource())
api.add_route("/api/v1/predict/ocr_prediction", OCRPredictionPredictorResource())
api.add_route("/api/v1/predict/category", CategoryPredictorResource())
api.add_route("/api/v1/predict/ingredient_list", IngredientListPredictorResource())
api.add_route("/api/v1/predict/lang", LanguagePredictorResource())
api.add_route("/api/v1/predict/lang/product", ProductLanguagePredictorResource())
api.add_route("/api/v1/products/dataset", UpdateDatasetResource())
api.add_route("/api/v1/images", ImageCollection())
api.add_route("/api/v1/images/crop", ImageCropResource())
api.add_route("/api/v1/image_predictions", ImagePredictionResource())
api.add_route("/api/v1/image_predictions/import", ImagePredictionImporterResource())
api.add_route("/api/v1/images/predict", ImagePredictorResource())
api.add_route("/api/v1/images/logos", ImageLogoResource())
api.add_route("/api/v1/images/logos/search", ImageLogoSearchResource())
api.add_route("/api/v1/images/logos/{logo_id:int}", ImageLogoDetailResource())
api.add_route("/api/v1/images/logos/{logo_id:int}/reset", ImageLogoResetResource())
api.add_route("/api/v1/images/logos/annotate", ImageLogoAnnotateResource())
api.add_route("/api/v1/images/logos/update", ImageLogoUpdateResource())
api.add_route("/api/v1/ann/search/{logo_id:int}", ANNResource())
api.add_route("/api/v1/ann/search", ANNResource())
api.add_route("/api/v1/questions/{barcode}", ProductQuestionsResource())
api.add_route("/api/v1/questions", QuestionsCollectionResource())
api.add_route("/api/v1/questions/random", RandomQuestionsResource())
api.add_route("/api/v1/questions/popular", PopularQuestionsResource())
api.add_route("/api/v1/questions/unanswered", UnansweredQuestionCollection())
api.add_route("/api/v1/status", StatusResource())
api.add_route("/api/v1/health", HealthResource())
api.add_route("/api/v1/users/statistics/{username}", UserStatisticsResource())
api.add_route("/api/v1/predictions", PredictionCollection())
api.add_route("/api/v1/annotation/collection", LogoAnnotationCollection())
api.add_route("/api/v1/batch/import", BatchJobImportResource())
api.add_route("/robots.txt", RobotsTxtResource())
