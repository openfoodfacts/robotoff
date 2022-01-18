import csv
import datetime
import functools
import io
import tempfile
from typing import List, Optional

import falcon
import orjson
import peewee
import requests
from falcon.media.validators import jsonschema
from falcon_cors import CORS
from falcon_multipart.middleware import MultipartMiddleware
from PIL import Image
from sentry_sdk.integrations.falcon import FalconIntegration

from robotoff import settings
from robotoff.app import schema
from robotoff.app.auth import BasicAuthDecodeError, basic_decode
from robotoff.app.core import get_insights, save_insight
from robotoff.app.middleware import DBConnectionMiddleware
from robotoff.insights.extraction import (
    DEFAULT_PREDICTION_TYPES,
    extract_ocr_predictions,
)
from robotoff.insights.question import QuestionFormatter, QuestionFormatterFactory
from robotoff.logos import generate_insights_from_annotated_logos
from robotoff.models import (
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    ProductInsight,
    batch_insert,
)
from robotoff.off import (
    OFFAuthentication,
    generate_image_path,
    get_product,
    get_server_type,
)
from robotoff.prediction.category.neural.category_classifier import CategoryClassifier
from robotoff.prediction.object_detection import ObjectDetectionModelRegistry
from robotoff.prediction.ocr.dataclass import OCRParsingException
from robotoff.prediction.types import PredictionType
from robotoff.products import get_product_dataset_etag
from robotoff.spellcheck import SPELLCHECKERS, Spellchecker
from robotoff.taxonomy import TaxonomyType, get_taxonomy, match_unprefixed_value
from robotoff.utils import get_image_from_url, get_logger, http_session
from robotoff.utils.es import get_es_client
from robotoff.utils.i18n import TranslationStore
from robotoff.utils.text import get_tag
from robotoff.utils.types import JSONType
from robotoff.workers.client import send_ipc_event

logger = get_logger()

settings.init_sentry(integrations=[FalconIntegration()])

es_client = get_es_client()

TRANSLATION_STORE = TranslationStore()
TRANSLATION_STORE.load()

###########
# IMPORTANT: remember to update documentation at doc/references/api.md if you change API
###########


class ProductInsightResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response, barcode: str):
        server_domain: Optional[str] = req.get_param("server_domain")
        response: JSONType = {}
        insights = [
            i.serialize()
            for i in get_insights(
                barcode=barcode, server_domain=server_domain, limit=None
            )
        ]

        if not insights:
            response["status"] = "no_insights"
        else:
            response["insights"] = insights
            response["status"] = "found"

        resp.media = response


class ProductInsightDetail:
    def on_get(self, req: falcon.Request, resp: falcon.Response, insight_id: str):
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
        keep_types: Optional[List[str]] = req.get_param_as_list(
            "insight_types", required=False
        )
        barcode: Optional[str] = req.get_param("barcode")
        country: Optional[str] = req.get_param("country")
        annotated: Optional[bool] = req.get_param_as_bool("annotated")
        annotation: Optional[int] = req.get_param_as_int("annotation")
        value_tag: str = req.get_param("value_tag")
        brands = req.get_param_as_list("brands") or None
        server_domain: Optional[str] = req.get_param("server_domain")

        if keep_types:
            # Limit the number of types to prevent slow SQL queries
            keep_types = keep_types[:10]

        if brands is not None:
            # Limit the number of brands to prevent slow SQL queries
            brands = brands[:10]

        get_insights_ = functools.partial(
            get_insights,
            keep_types=keep_types,
            country=country,
            server_domain=server_domain,
            value_tag=value_tag,
            brands=brands,
            annotated=annotated,
            annotation=annotation,
            barcode=barcode,
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
        insight_type: Optional[str] = req.get_param("type")
        country: Optional[str] = req.get_param("country")
        value_tag: Optional[str] = req.get_param("value_tag")
        server_domain: Optional[str] = req.get_param("server_domain")
        count: int = req.get_param_as_int("count", default=1, min_value=1, max_value=50)

        keep_types = [insight_type] if insight_type else None
        insights: List[ProductInsight] = list(
            get_insights(
                keep_types=keep_types,
                country=country,
                value_tag=value_tag,
                order_by="random",
                server_domain=server_domain,
                limit=count,
            )
        )

        resp.media = {"insights": [insight.serialize() for insight in insights]}


def parse_auth(req: falcon.Request) -> Optional[OFFAuthentication]:
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


class AnnotateInsightResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        insight_id = req.get_param("insight_id", required=True)
        annotation = req.get_param_as_int(
            "annotation", required=True, min_value=-1, max_value=1
        )

        update = req.get_param_as_bool("update", default=True)
        data = req.get_param_as_json("data")

        auth: Optional[OFFAuthentication] = parse_auth(req)

        username = auth.get_username() if auth else "unknown annotator"
        logger.info(
            "New annotation received from {} (annotation: {}, insight: {})".format(
                username, annotation, insight_id
            )
        )

        annotation_result = save_insight(
            insight_id, annotation, update=update, data=data, auth=auth
        )

        resp.media = {
            "status": annotation_result.status,
            "description": annotation_result.description,
        }


class IngredientSpellcheckResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        self.spellcheck(req, resp)

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        self.spellcheck(req, resp)

    def spellcheck(self, req: falcon.Request, resp: falcon.Response):
        text = req.get_param("text")
        if text is None:
            barcode = req.get_param("barcode")
            if barcode is None:
                raise falcon.HTTPBadRequest("text or barcode is required.")

            product = get_product(barcode) or {}
            text = product.get("ingredients_text_fr")
            if text is None:
                resp.media = {"status": "not_found"}
                return

        index_name = req.get_param("index", default="product_all")
        confidence = req.get_param_as_float("confidence", default=0.5)
        pipeline = req.get_param_as_list("pipeline") or None
        safe = req.get_param_as_bool("safe", blank_as_true=False)

        if safe is not None and pipeline:
            raise falcon.HTTPBadRequest(
                "pipeline and safe parameters cannot be used together"
            )

        if pipeline:
            for item in pipeline:
                if item not in SPELLCHECKERS:
                    raise falcon.HTTPBadRequest(f"unknown pipeline item: {item}")
        elif safe:
            pipeline = ["patterns", "percentages", "vocabulary"]

        spellchecker = Spellchecker.load(
            client=es_client,
            pipeline=pipeline,
            index_name=index_name,
            confidence=confidence,
        )
        correction_item = spellchecker.correct(text)

        resp.media = {
            "text": text,
            "corrected": correction_item.latest_correction,
            "corrections": correction_item.corrections,
        }


class NutrientPredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        ocr_url = req.get_param("ocr_url", required=True)

        if not ocr_url.endswith(".json"):
            raise falcon.HTTPBadRequest("a JSON file is expected")

        try:
            product_predictions = extract_ocr_predictions(
                ocr_url, [PredictionType.nutrient]
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

        if not product_predictions:
            resp.media = {
                "nutrients": {},
            }
        else:
            nutrient_predictions = product_predictions[PredictionType.nutrient]
            resp.media = nutrient_predictions.to_dict()


class OCRInsightsPredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        ocr_url = req.get_param("ocr_url", required=True)

        try:
            insights = extract_ocr_predictions(ocr_url, DEFAULT_PREDICTION_TYPES)

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
            "insights": insights,
        }


class CategoryPredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        barcode = req.get_param("barcode", required=True)
        deepest_only = req.get_param_as_bool("deepest_only", default=False)

        categories = []

        product = get_product(barcode)
        if product:
            predicted = CategoryClassifier(
                get_taxonomy(TaxonomyType.category.name)
            ).predict(product, deepest_only)

            if predicted:
                categories = [
                    {
                        "category": prediction.category,
                        "confidence": prediction.confidence,
                    }
                    for prediction in predicted
                ]

        resp.media = {"categories": categories}


class UpdateDatasetResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        send_ipc_event("download_dataset")

        resp.media = {
            "status": "scheduled",
        }

    def on_get(self, req: falcon.Request, resp: falcon.Response):
        resp.media = {
            "etag": get_product_dataset_etag(),
        }


class ImageImporterResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        barcode = req.get_param("barcode", required=True)
        image_url = req.get_param("image_url", required=True)
        ocr_url = req.get_param("ocr_url", required=True)
        server_domain = req.get_param("server_domain", required=True)

        if server_domain != settings.OFF_SERVER_DOMAIN:
            logger.info("Rejecting image import from {}".format(server_domain))
            resp.media = {
                "status": "rejected",
            }
            return

        send_ipc_event(
            "import_image",
            {
                "barcode": barcode,
                "image_url": image_url,
                "ocr_url": ocr_url,
                "server_domain": server_domain,
            },
        )

        resp.media = {
            "status": "scheduled",
        }


class ImageCropResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        image_url = req.get_param("image_url", required=True)
        y_min = req.get_param_as_float("y_min", required=True)
        x_min = req.get_param_as_float("x_min", required=True)
        y_max = req.get_param_as_float("y_max", required=True)
        x_max = req.get_param_as_float("x_max", required=True)
        image = get_image_from_url(image_url)

        if image is None:
            raise falcon.HTTPBadRequest("invalid image")

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
        timestamp = datetime.datetime.utcnow()
        inserts = []

        for prediction in req.media["predictions"]:
            server_domain: str = prediction.get(
                "server_domain", settings.OFF_SERVER_DOMAIN
            )
            server_type: str = get_server_type(server_domain).name
            source_image = generate_image_path(
                prediction["barcode"], prediction.pop("image_id")
            )
            inserts.append(
                {
                    "timestamp": timestamp,
                    "server_domain": server_domain,
                    "server_type": server_type,
                    "source_image": source_image,
                    **prediction,
                }
            )

        inserted = batch_insert(ImagePrediction, inserts)
        logger.info("{} image predictions inserted".format(inserted))


class ImagePredictionFetchResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        count: int = req.get_param_as_int("count", min_value=1, default=25)
        model_name: Optional[str] = req.get_param("model_name")
        type_: Optional[str] = req.get_param("type")
        model_version: Optional[str] = req.get_param("model_version")
        server_domain: Optional[str] = req.get_param("server_domain")
        barcode: Optional[str] = req.get_param("barcode")
        min_confidence: Optional[float] = req.get_param_as_float("min_confidence")
        random: bool = req.get_param_as_bool("random", default=True)

        where_clauses = []

        if model_name is not None:
            where_clauses.append(ImagePrediction.model_name == model_name)

        if model_version is not None:
            where_clauses.append(ImagePrediction.model_version == model_version)

        if type_ is not None:
            where_clauses.append(ImagePrediction.type == type_)

        if server_domain:
            where_clauses.append(ImageModel.server_domain == server_domain)

        if min_confidence is not None:
            where_clauses.append(ImagePrediction.max_confidence >= min_confidence)

        if barcode is not None:
            where_clauses.append(ImageModel.barcode == barcode)

        query = ImagePrediction.select().join(ImageModel)

        if where_clauses:
            query = query.where(*where_clauses)

        if random:
            query = query.order_by(peewee.fn.Random())

        query = query.limit(count)
        items = [item.to_dict() for item in query.iterator()]
        resp.media = {"predictions": items}


class ImagePredictorResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        image_url = req.get_param("image_url", required=True)
        models: List[str] = req.get_param_as_list("models", required=True)

        available_models = ObjectDetectionModelRegistry.get_available_models()

        for model_name in models:
            if model_name not in available_models:
                raise falcon.HTTPBadRequest(
                    "invalid_model",
                    "unknown model {}, available models: {}"
                    "".format(model_name, ", ".join(available_models)),
                )

        output_image = req.get_param_as_bool("output_image")

        if output_image is None:
            output_image = False

        if output_image and len(models) != 1:
            raise falcon.HTTPBadRequest(
                "invalid_request",
                "a single model must be specified with the `models` parameter "
                "when `output_image` is True",
            )

        image = get_image_from_url(image_url, session=http_session)

        if image is None:
            logger.info("Could not fetch image: {}".format(image_url))
            return

        predictions = {}

        for model_name in models:
            model = ObjectDetectionModelRegistry.get(model_name)
            result = model.detect_from_image(image, output_image=output_image)

            if output_image:
                image_response(result.boxed_image, resp)
                return
            else:
                predictions[model_name] = result.to_json()

        resp.media = {"predictions": predictions}


def image_response(image: Image.Image, resp: falcon.Response) -> None:
    resp.content_type = "image/jpeg"
    fp = io.BytesIO()
    image.save(fp, "JPEG")
    resp.stream_len = fp.tell()
    fp.seek(0)
    resp.stream = fp


class ImageLogoResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        logo_ids: Optional[List[str]] = req.get_param_as_list(
            "logo_ids", required=False
        )

        if logo_ids is not None:
            self.fetch_logos(logo_ids, resp)
        else:
            self.search(req, resp)

    def search(self, req: falcon.Request, resp: falcon.Response):
        count: int = req.get_param_as_int(
            "count", min_value=1, max_value=2000, default=25
        )
        type_: Optional[str] = req.get_param("type")
        barcode: Optional[str] = req.get_param("barcode")
        value: Optional[str] = req.get_param("value")
        min_confidence: Optional[float] = req.get_param_as_float("min_confidence")
        random: bool = req.get_param_as_bool("random", default=False)
        server_domain: Optional[str] = req.get_param("server_domain")
        annotated: bool = req.get_param_as_bool("annotated", default=False)

        where_clauses = [LogoAnnotation.annotation_value.is_null(not annotated)]
        join_image_prediction = False
        join_image_model = False

        if server_domain:
            where_clauses.append(ImageModel.server_domain == server_domain)
            join_image_model = True

        if min_confidence is not None:
            where_clauses.append(ImagePrediction.max_confidence >= min_confidence)
            join_image_prediction = True

        if barcode is not None:
            where_clauses.append(ImageModel.barcode == barcode)
            join_image_model = True

        if type_ is not None:
            where_clauses.append(LogoAnnotation.annotation_type == type_)

        if value is not None:
            value_tag = get_tag(value)
            where_clauses.append(LogoAnnotation.annotation_value_tag == value_tag)

        query = LogoAnnotation.select()
        join_image_prediction = join_image_prediction or join_image_model

        if join_image_prediction:
            query = query.join(ImagePrediction)

            if join_image_model:
                query = query.join(ImageModel)

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

    def fetch_logos(self, logo_ids: List[str], resp: falcon.Response):
        logos = []
        for logo in (
            LogoAnnotation.select()
            .join(ImagePrediction)
            .join(ImageModel)
            .where(LogoAnnotation.id.in_(logo_ids))
            .iterator()
        ):
            logo_dict = logo.to_dict()
            image_prediction = logo_dict.pop("image_prediction")
            logo_dict["image"] = image_prediction["image"]
            logos.append(logo_dict)

        resp.media = {"logos": logos, "count": len(logos)}


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
        logo = LogoAnnotation.get_or_none(id=logo_id)

        if logo is None:
            resp.status = falcon.HTTP_404
            return

        type_ = req.media["type"]
        value = req.media["value"] or None
        updated = False

        if type_ != logo.annotation_type:
            logo.annotation_type = type_
            updated = True

        if value != logo.annotation_value:
            logo.annotation_value = value

            if value is not None:
                value_tag = get_tag(value)
                logo.annotation_value_tag = value_tag
                logo.taxonomy_value = match_unprefixed_value(value_tag, type_)
            else:
                logo.annotation_value_tag = None
                logo.taxonomy_value = None

            updated = True

        if updated:
            auth = parse_auth(req)
            username = None if auth is None else auth.get_username()
            logo.username = username
            logo.completed_at = datetime.datetime.utcnow()
            logo.save()

        resp.status = falcon.HTTP_204


class ImageLogoAnnotateResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        server_domain = req.media.get("server_domain", settings.OFF_SERVER_DOMAIN)
        annotations = req.media["annotations"]
        auth = parse_auth(req)
        username = None if auth is None else auth.get_username()
        completed_at = datetime.datetime.utcnow()
        annotated_logos = []

        for annotation in annotations:
            logo_id = annotation["logo_id"]
            type_ = annotation["type"]
            value = annotation["value"] or None
            logo = LogoAnnotation.get_by_id(logo_id)

            if value is not None:
                logo.annotation_value = value
                value_tag = get_tag(value)
                logo.annotation_value_tag = value_tag
                logo.taxonomy_value = match_unprefixed_value(value_tag, type_)

            logo.annotation_type = type_
            logo.username = username
            logo.completed_at = completed_at
            logo.save()
            annotated_logos.append(logo)

        generate_insights_from_annotated_logos(annotated_logos, server_domain)


class ImageLogoUpdateResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        source_value = req.get_param("source_value", required=True)
        source_type = req.get_param("source_type", required=True)
        target_value = req.get_param("target_value", required=True)
        target_type = req.get_param("target_type", required=True)

        auth = parse_auth(req)
        username = None if auth is None else auth.get_username()
        completed_at = datetime.datetime.utcnow()

        target_value_tag = get_tag(target_value)
        source_value_tag = get_tag(source_value)
        taxonomy_value = match_unprefixed_value(target_value_tag, target_type)

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


class WebhookProductResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        barcode = req.get_param("barcode", required=True)
        action = req.get_param("action", required=True)
        server_domain = req.get_param("server_domain", required=True)

        if server_domain != settings.OFF_SERVER_DOMAIN:
            logger.info("Rejecting webhook event from {}".format(server_domain))
            resp.media = {
                "status": "rejected",
            }
            return

        logger.info(
            "New webhook event received for product {} (action: {}, "
            "domain: {})".format(barcode, action, server_domain)
        )

        if action not in ("updated", "deleted"):
            raise falcon.HTTPBadRequest(
                title="invalid_action",
                description="action must be one of " "`deleted`, `updated`",
            )

        if action == "updated":
            send_ipc_event(
                "product_updated", {"barcode": barcode, "server_domain": server_domain}
            )

        elif action == "deleted":
            send_ipc_event(
                "product_deleted", {"barcode": barcode, "server_domain": server_domain}
            )

        resp.media = {
            "status": "scheduled",
        }


class ProductQuestionsResource:
    """Get a question about a product to confirm/infirm an insight

    see also doc/explanation/questions.md
    """

    def on_get(self, req: falcon.Request, resp: falcon.Response, barcode: str):
        response: JSONType = {}
        count: int = req.get_param_as_int("count", min_value=1) or 1
        lang: str = req.get_param("lang", default="en")
        server_domain: Optional[str] = req.get_param("server_domain")

        keep_types = QuestionFormatterFactory.get_default_types()
        insights = list(
            get_insights(
                barcode=barcode,
                keep_types=keep_types,
                server_domain=server_domain,
                limit=count,
            )
        )

        if not insights:
            response["questions"] = []
            response["status"] = "no_questions"
        else:
            questions: List[JSONType] = []

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


def get_questions_resource_on_get(
    req: falcon.Request, resp: falcon.Response, order_by: str
):
    response: JSONType = {}
    count: int = req.get_param_as_int("count", min_value=1, default=25)
    lang: str = req.get_param("lang", default="en")
    keep_types: Optional[List[str]] = req.get_param_as_list(
        "insight_types", required=False
    )
    country: Optional[str] = req.get_param("country")
    value_tag: str = req.get_param("value_tag")
    brands = req.get_param_as_list("brands") or None
    server_domain: Optional[str] = req.get_param("server_domain")
    reserved_barcode: Optional[bool] = req.get_param_as_bool(
        "reserved_barcode", default=False
    )

    if reserved_barcode:
        # Include all results, including non reserved barcodes
        reserved_barcode = None

    if keep_types is None:
        keep_types = QuestionFormatterFactory.get_default_types()
    else:
        # Limit the number of types to prevent slow SQL queries
        keep_types = keep_types[:10]

    if brands is not None:
        # Limit the number of brands to prevent slow SQL queries
        brands = brands[:10]

    get_insights_ = functools.partial(
        get_insights,
        keep_types=keep_types,
        country=country,
        server_domain=server_domain,
        value_tag=value_tag,
        brands=brands,
        order_by=order_by,
        reserved_barcode=reserved_barcode,
    )

    insights = list(get_insights_(limit=count))
    response["count"] = get_insights_(count=True)
    # This code should be merged with the one in ProductQuestionsResource.get
    if not insights:
        response["questions"] = []
        response["status"] = "no_questions"
    else:
        questions: List[JSONType] = []

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
        keep_types: Optional[List[str]] = req.get_param_as_list(
            "insight_types", required=False
        )

        if keep_types is not None:
            keep_types = keep_types[:10]

        barcode = req.get_param("barcode")
        annotated = req.get_param_as_bool("annotated", blank_as_true=False)
        value_tag = req.get_param("value_tag")

        insights_iter = get_insights(
            barcode=barcode,
            keep_types=keep_types,
            annotated=annotated,
            value_tag=value_tag,
            limit=None,
        )

        writer = None

        with tempfile.TemporaryFile("w+", newline="") as temp_f:
            for insight in insights_iter:
                serial = orjson.loads(orjson.dumps(insight.to_dict()))

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


cors = CORS(
    allow_all_origins=True,
    allow_all_headers=True,
    allow_all_methods=True,
    allow_credentials_all_origins=True,
    max_age=600,
)

api = falcon.API(
    middleware=[cors.middleware, MultipartMiddleware(), DBConnectionMiddleware()]
)

json_handler = falcon.media.JSONHandler(dumps=orjson.dumps, loads=orjson.loads)
extra_handlers = {
    "application/json": json_handler,
}

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
api.add_route("/api/v1/predict/ingredients/spellcheck", IngredientSpellcheckResource())
api.add_route("/api/v1/predict/nutrient", NutrientPredictorResource())
api.add_route("/api/v1/predict/ocr_insights", OCRInsightsPredictorResource())
api.add_route("/api/v1/predict/category", CategoryPredictorResource())
api.add_route("/api/v1/products/dataset", UpdateDatasetResource())
api.add_route("/api/v1/webhook/product", WebhookProductResource())
api.add_route("/api/v1/images/import", ImageImporterResource())
api.add_route("/api/v1/images/crop", ImageCropResource())
api.add_route("/api/v1/images/predictions/import", ImagePredictionImporterResource())
api.add_route("/api/v1/images/predictions", ImagePredictionFetchResource())
api.add_route("/api/v1/images/predict", ImagePredictorResource())
api.add_route("/api/v1/images/logos", ImageLogoResource())
api.add_route("/api/v1/images/logos/{logo_id:int}", ImageLogoDetailResource())
api.add_route("/api/v1/images/logos/annotate", ImageLogoAnnotateResource())
api.add_route("/api/v1/images/logos/update", ImageLogoUpdateResource())
api.add_route("/api/v1/questions/{barcode}", ProductQuestionsResource())
api.add_route("/api/v1/questions/random", RandomQuestionsResource())
api.add_route("/api/v1/questions/popular", PopularQuestionsResource())
api.add_route("/api/v1/status", StatusResource())
api.add_route("/api/v1/health", HealthResource())
api.add_route("/api/v1/dump", DumpResource())
api.add_route("/api/v1/users/statistics/{username}", UserStatisticsResource())
