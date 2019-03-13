import io
import itertools
from typing import List

import dataclasses

import falcon
from falcon_cors import CORS
from falcon_multipart.middleware import MultipartMiddleware

from robotoff.app.core import (normalize_lang,
                               parse_product_json,
                               get_insights,
                               get_random_insight,
                               save_insight, CATEGORY_PRODUCT_FIELDS)
from robotoff.app.middleware import DBConnectionMiddleware
from robotoff.ingredients import generate_corrections, generate_corrected_text
from robotoff.insights._enum import InsightType
from robotoff.insights.question import QuestionFormatterFactory, \
    QuestionFormatter
from robotoff.off import get_product
from robotoff.products import get_product_dataset_etag
from robotoff.taxonomy import TAXONOMY_STORES, TaxonomyType, Taxonomy
from robotoff.utils import get_logger
from robotoff.utils.es import get_es_client
from robotoff.utils.i18n import TranslationStore
from robotoff.utils.types import JSONType
from robotoff.workers.client import send_ipc_event

logger = get_logger()
es_client = get_es_client()

CATEGORY_TAXONOMY: Taxonomy = TAXONOMY_STORES[TaxonomyType.category.name].get()
TRANSLATION_STORE = TranslationStore()
TRANSLATION_STORE.load()


class CategoryPredictionResource:
    def on_get(self, req, resp):
        response = {}

        country = req.get_param('country')
        lang = normalize_lang(req.get_param('lang'))

        insight = get_random_insight(InsightType.category.name, country)

        if not insight:
            response['status'] = "no_prediction_left"

        else:
            product = get_product(insight.barcode,
                                  CATEGORY_PRODUCT_FIELDS)
            response['product'] = parse_product_json(product, lang)
            response['task_id'] = str(insight.id)

            category_tag = insight.data['category']
            predicted_category_name = CATEGORY_TAXONOMY.get_localized_name(
                category_tag, lang)
            response['prediction'] = {
                'confidence': insight.data['confidence'],
                'id': category_tag,
                'name': predicted_category_name,
            }

        resp.media = response


class ProductInsightResource:
    def on_get(self, req, resp, barcode):
        response = {}
        insights = [i.serialize() for i in get_insights(barcode)]

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


class CategoryAnnotateResource:
    def on_post(self, req, resp):
        task_id = req.get_param('task_id', required=True)
        annotation = req.get_param_as_int('annotation', required=True,
                                          min=-1, max=1)

        update = req.get_param_as_bool('save')

        if update is None:
            update = True

        save_insight(task_id, annotation, update=update)
        resp.media = {
            'status': 'saved',
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


class ProductImporterResource:
    def on_post(self, req, resp):
        barcode = req.get_param('barcode', required=True)

        resp.media = {
            'status': 'scheduled',
        }


class ProductQuestionsResource:
    def on_get(self, req, resp, barcode):
        response = {}
        count: int = req.get_param_as_int('count', min=1) or 1
        lang: str = req.get_param('lang', default='en')

        keep_types = QuestionFormatterFactory.get_available_types()
        insights = list(get_insights(barcode, keep_types, count))

        if not insights:
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
api.add_route('/api/v1/categories/predictions', CategoryPredictionResource())
api.add_route('/api/v1/categories/annotate', CategoryAnnotateResource())
api.add_route('/api/v1/predict/ingredients/spellcheck',
              IngredientSpellcheckResource())
api.add_route('/api/v1/products/dataset',
              UpdateDatasetResource())
api.add_route('/api/v1/products/import',
              ProductImporterResource())
api.add_route('/api/v1/images/import', ImageImporterResource())
api.add_route('/api/v1/questions/{barcode}', ProductQuestionsResource())
