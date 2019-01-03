import falcon
from falcon_cors import CORS

from robotoff.app.core import (normalize_lang,
                               get_next_product,
                               parse_product_json,
                               get_category_name,
                               save_annotation)


class CategoryPredictionResource:
    def on_get(self, req, resp):
        response = {}

        campaign = req.get_param('campaign')
        country = req.get_param('country')
        category = req.get_param('category')
        lang = normalize_lang(req.get_param('lang'))

        result = get_next_product(campaign, country, category)

        if result is None:
            response['status'] = "no_prediction_left"

        else:
            task, product = result
            response['product'] = parse_product_json(product, lang)
            response['task_id'] = str(task.id)

            predicted_category_name = get_category_name(task.predicted_category,
                                                        lang)
            response['prediction'] = {
                'confidence': task.confidence,
                'id': task.predicted_category,
                'name': predicted_category_name,
            }

        resp.media = response


class CategoryAnnotateResource:
    def on_post(self, req, resp):
        task_id = req.get_param('task_id', required=True)
        annotation = req.get_param_as_int('annotation', required=True,
                                          min=-1, max=1)

        save = req.get_param_as_bool('save')

        if save is None:
            save = True

        save_annotation(task_id, annotation, save=save)
        resp.media = {
            'status': 'saved',
        }


cors = CORS(allow_all_origins=True,
            allow_all_headers=True,
            allow_all_methods=True)

api = falcon.API(middleware=[cors.middleware])
# Parse form parameters
api.req_options.auto_parse_form_urlencoded = True
api.add_route('/api/v1/categories/predictions', CategoryPredictionResource())
api.add_route('/api/v1/categories/annotate', CategoryAnnotateResource())
