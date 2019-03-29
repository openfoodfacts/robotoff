import io
import itertools
from typing import List, Optional

import dataclasses

import falcon
from falcon_cors import CORS
from falcon_multipart.middleware import MultipartMiddleware

from robotoff import settings
from robotoff.app.core import (get_insights,
                               get_random_insight,
                               save_insight)
from robotoff.app.middleware import DBConnectionMiddleware
from robotoff.ingredients import generate_corrections, generate_corrected_text
from robotoff.insights._enum import InsightType
from robotoff.insights.question import QuestionFormatterFactory, \
    QuestionFormatter
from robotoff.products import get_product_dataset_etag
from robotoff.taxonomy import TAXONOMY_STORES, TaxonomyType, Taxonomy
from robotoff.utils import get_logger
from robotoff.utils.es import get_es_client
from robotoff.utils.i18n import TranslationStore
from robotoff.utils.types import JSONType
from robotoff.workers.client import send_ipc_event

import sentry_sdk
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware

logger = get_logger()
es_client = get_es_client()

CATEGORY_TAXONOMY: Taxonomy = TAXONOMY_STORES[TaxonomyType.category.name].get()
TRANSLATION_STORE = TranslationStore()
TRANSLATION_STORE.load()


def init_sentry(app):
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN)
        return SentryWsgiMiddleware(app)

    return app


class ProductInsightResource:
    def on_get(self, req, resp, barcode):
        response = {}
        insights = [i.serialize() for i in get_insights(barcode=barcode)]

        if not insights:
            response['status'] = "no_insights"
        else:
            response['insights'] = insights
            response['status'] = "found"

        resp.media = response


class RandomInsightResource:
    def on_get(self, req, resp):
        insight_type = req.get_param('type') or None
        country = req.get_param('country') or None
        response = {}

        insight = get_random_insight(insight_type, country)

        if not insight:
            response['status'] = "no_insights"
        else:
            response['insight'] = insight.serialize()
            response['status'] = "found"

        resp.media = response


class AnnotateInsightResource:
    def on_post(self, req, resp):
        insight_id = req.get_param('insight_id', required=True)
        annotation = req.get_param_as_int('annotation', required=True,
                                          min=-1, max=1)

        update = req.get_param_as_bool('update')

        if update is None:
            update = True

        annotation_result = save_insight(insight_id, annotation, update=update)

        resp.media = {
            'status': annotation_result.status,
            'description': annotation_result.description,
        }


class IngredientSpellcheckResource:
    def on_post(self, req, resp):
        text = req.get_param('text', required=True)

        corrections = generate_corrections(es_client, text, confidence=1)
        term_corrections = list(itertools.chain
                                .from_iterable((c.term_corrections
                                                for c in corrections)))

        resp.media = {
            'corrections': [dataclasses.asdict(c) for c in corrections],
            'text': text,
            'corrected': generate_corrected_text(term_corrections, text),
        }


class UpdateDatasetResource:
    def on_post(self, req, resp):
        send_ipc_event('download_dataset')

        resp.media = {
            'status': 'scheduled',
        }

    def on_get(self, req, resp):
        resp.media = {
            'etag': get_product_dataset_etag(),
        }


class InsightImporterResource:
    def on_post(self, req, resp):
        logger.info("New insight import request")
        insight_type = req.get_param('type', required=True)

        if insight_type not in (t.name for t in InsightType):
            raise falcon.HTTPBadRequest(description="unknown insight type: "
                                                    "'{}'".format(insight_type))

        content = req.get_param('file', required=True)

        logger.info("Insight type: '{}'".format(insight_type))

        lines = [l for l in io.TextIOWrapper(content.file)]

        send_ipc_event('import_insights', {
            'insight_type': insight_type,
            'items': lines,
        })

        logger.info("Import scheduled")

        resp.media = {
            'status': 'scheduled',
        }


class ImageImporterResource:
    def on_post(self, req, resp):
        barcode = req.get_param('barcode', required=True)
        image_url = req.get_param('image_url', required=True)
        ocr_url = req.get_param('ocr_url', required=True)

        send_ipc_event('import_image', {
            'barcode': barcode,
            'image_url': image_url,
            'ocr_url': ocr_url,
        })

        resp.media = {
            'status': 'scheduled',
        }


class WebhookProductResource:
    def on_post(self, req, resp):
        barcode = req.get_param('barcode', required=True)
        action = req.get_param('action', required=True)

        if action not in ('created', 'updated', 'deleted'):
            raise falcon.HTTPBadRequest(title="invalid_action",
                                        description="action must be one of "
                                                    "`created`, `deleted`, `updated`")

        if action == 'created':
            send_ipc_event('product_created', {
                'barcode': barcode,
            })

        elif action == 'updated':
            updated_fields = req.get_param_as_list('updated_fields', required=True)

            send_ipc_event('product_updated', {
                'barcode': barcode,
                'updated_fields': updated_fields,
            })

        elif action == 'deleted':
            send_ipc_event('product_deleted', {
                'barcode': barcode,
            })

        resp.media = {
            'status': 'scheduled',
        }


class ProductQuestionsResource:
    def on_get(self, req, resp, barcode):
        response = {}
        count: int = req.get_param_as_int('count', min=1) or 1
        lang: str = req.get_param('lang', default='en')

        keep_types = QuestionFormatterFactory.get_available_types()
        insights = list(get_insights(barcode=barcode,
                                     keep_types=keep_types,
                                     count=count))

        if not insights:
            response['questions'] = []
            response['status'] = "no_questions"
        else:
            questions: List[JSONType] = []

            for insight in insights:
                formatter_cls = QuestionFormatterFactory.get(insight.type)
                formatter: QuestionFormatter = formatter_cls(TRANSLATION_STORE)
                question = formatter.format_question(insight, lang)
                questions.append(question.serialize())

            response['questions'] = questions
            response['status'] = "found"

        resp.media = response


class RandomQuestionsResource:
    def on_get(self, req, resp):
        response = {}
        count: int = req.get_param_as_int('count', min=1) or 1
        lang: str = req.get_param('lang', default='en')
        keep_types: Optional[List[str]] = req.get_param_as_list(
            'insight_types', required=False)
        country: Optional[str] = req.get_param('country') or None
        brands = req.get_param_as_list('brands') or None

        if keep_types is None:
            keep_types = QuestionFormatterFactory.get_available_types()
        else:
            # Limit the number of types to prevent slow SQL queries
            keep_types = keep_types[:10]

        if brands is not None:
            # Limit the number of brands to prevent slow SQL queries
            brands = brands[:10]

        insights = list(get_insights(keep_types=keep_types,
                                     count=count,
                                     country=country,
                                     brands=brands))

        if not insights:
            response['questions'] = []
            response['status'] = "no_questions"
        else:
            questions: List[JSONType] = []

            for insight in insights:
                formatter_cls = QuestionFormatterFactory.get(insight.type)

                if formatter_cls is None:
                    continue

                formatter: QuestionFormatter = formatter_cls(TRANSLATION_STORE)
                question = formatter.format_question(insight, lang)
                questions.append(question.serialize())

            response['questions'] = questions
            response['status'] = "found"

        resp.media = response


cors = CORS(allow_all_origins=True,
            allow_all_headers=True,
            allow_all_methods=True)

api = falcon.API(middleware=[cors.middleware,
                             MultipartMiddleware(),
                             DBConnectionMiddleware()])
# Parse form parameters
api.req_options.auto_parse_form_urlencoded = True
api.add_route('/api/v1/insights/{barcode}', ProductInsightResource())
api.add_route('/api/v1/insights/random', RandomInsightResource())
api.add_route('/api/v1/insights/annotate', AnnotateInsightResource())
api.add_route('/api/v1/insights/import', InsightImporterResource())
api.add_route('/api/v1/predict/ingredients/spellcheck',
              IngredientSpellcheckResource())
api.add_route('/api/v1/products/dataset',
              UpdateDatasetResource())
api.add_route('/api/v1/webhook/product',
              WebhookProductResource())
api.add_route('/api/v1/images/import', ImageImporterResource())
api.add_route('/api/v1/questions/{barcode}', ProductQuestionsResource())
api.add_route('/api/v1/questions/random', RandomQuestionsResource())

api = init_sentry(api)
