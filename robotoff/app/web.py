import logging
import uuid

import peewee
from flask import Flask, request, render_template, session, jsonify

import requests

from robotoff import settings
from robotoff.app.models import CategorizationTask
from robotoff.categories import parse_category_json

category_json = parse_category_json(settings.DATA_DIR / 'categories.min.json')

app = Flask(__name__)
http_session = requests.Session()
API_URL = "https://world.openfoodfacts.org/api/v0"
PRODUCT_URL = API_URL + "/product"

# POST_URL = "https://world.openfoodfacts.net/cgi/product_jqm2.pl"
# AUTH = ("off", "off")

POST_URL = "https://world.openfoodfacts.org/cgi/product_jqm2.pl"
AUTH = ("roboto-app", "4mbN9wJp8LBShcH")

app.secret_key = b'k@\xcf\xb0\xfb\x94\xb2=3cJ7Q\xf1F\xd5'


def generate_session_id():
    return str(uuid.uuid4())


def set_session_id():
    if 'session_id' not in session:
        session['session_id'] = generate_session_id()


def get_session_id():
    return session['session_id']


def get_product(product_id, **kwargs):
    url = PRODUCT_URL + "/{}.json".format(product_id)
    r = http_session.get(url, params=kwargs)

    if r.status_code != 200:
        return

    data = r.json()

    if data['status_verbose'] != 'product found':
        return

    return data['product']


def normalize_lang(lang):
    if lang is None:
        return

    if '-' in lang:
        return lang.split('-')[0]

    return lang


def get_category_name(identifier, lang):
    if identifier not in category_json:
        return identifier

    category = category_json[identifier]
    category_names = category['name']

    if lang in category_names:
        return category_names[lang]

    if 'en' in category_names:
        return category_names['en']

    return identifier


def parse_product_json(data, lang=None):
    product = {
        'image_url': data.get('image_front_url'),
        'ingredients_texts': data.get('ingredients_text'),
        'product_name': data.get('product_name'),
        'brands': data.get('brands'),
        'categories_tags': list(set(data.get('categories_tags', []))),
    }

    if lang is None:
        domain = "https://world.openfoodfacts.org"
    else:
        domain = "https://{}.openfoodfacts.org".format(lang)

    product['product_link'] = "{}/product/{}".format(domain, data.get('code'))

    return product


def get_next_product(campaign: str=None):
    app.logger.info("Campaign: {}".format(campaign))

    attempts = 0
    while True:
        attempts += 1

        if attempts > 4:
            return

        query = (CategorizationTask.select()
                                   .where(CategorizationTask.attributed_at
                                          .is_null()))

        if campaign is not None:
            query = query.where(CategorizationTask.campaign ==
                                campaign).order_by(peewee.fn.Random())
        else:
            query = query.where(CategorizationTask.campaign.is_null()
                                ).order_by(CategorizationTask
                                           .category_depth.desc())

        random_task_list = list(query.limit(1))

        if not random_task_list:
            return

        random_task = random_task_list[0]
        product = get_product(random_task.product_id)

        # Product may be None if not found
        if product:
            return random_task, product
        else:
            random_task.outdated = True
            random_task.save()
            app.logger.info("Product not found")


def render_next_product(campaign: str=None):
    result = get_next_product(campaign)

    if result is None:
        return render_template('index.html', no_product=True)

    task, product = result
    task.set_attribution(session_id=get_session_id())
    language = normalize_lang(request.accept_languages.best)
    context = parse_product_json(product, language)
    context['task_id'] = str(task.id)
    context['confidence'] = task.confidence
    predicted_category_name = get_category_name(task.predicted_category,
                                                language)
    context['predicted_category_name'] = predicted_category_name
    context['predicted_category'] = task.predicted_category

    if campaign is not None:
        context['post_endpoint'] = '/campaign/{}'.format(campaign)
    else:
        context['post_endpoint'] = '/'

    return render_template("index.html", **context)


def save_categories(product_id, categories):
    categories = list(set(c for c in categories if c))

    params = {
        'code': product_id,
        'categories': ','.join(categories),
        'user_id': AUTH[0],
        'password': AUTH[1],
    }

    r = http_session.get(POST_URL, params=params)
    r.raise_for_status()
    json = r.json()

    status = json.get('status_verbose')

    if status != "fields saved":
        app.logger.warn("Unexpected status during category update: {}".format(status))


@app.route('/')
@app.route('/campaign/<campaign>')
def categorize_get(campaign=None):
    set_session_id()
    return render_next_product(campaign)


def save_annotation(task_id: str, annotation: int, session_id: str):
    try:
        task = CategorizationTask.get_by_id(task_id)
    except CategorizationTask.DoesNotExist:
        task = None

    if (not task or
            task.attributed_to_session_id != session_id or
            task.annotation is not None):
        return

    task.annotation = annotation
    task.save()

    if annotation == 1:
        current_categories = request.form['current_categories'].split(',')
        current_categories.append(task.predicted_category)
        save_categories(task.product_id, current_categories)

    task.set_completion(session_id=session_id)


@app.route('/', methods=['POST'])
@app.route('/campaign/<campaign>', methods=['POST'])
def categorize_post(campaign=None):
    set_session_id()
    task_id = request.form['task_id']
    annotation = int(request.form['annotation'])
    session_id = get_session_id()
    save_annotation(task_id, annotation, session_id)
    return render_next_product(campaign)


@app.route('/api/v1/categories/predictions', methods=['GET'])
def api_get_categories_prediction():
    session_id = request.args.get('session_id')

    response = {}

    if session_id is None:
        session_id = generate_session_id()
        response['session_id'] = session_id

    campaign = request.args.get('campaign')
    lang = normalize_lang(request.args.get('lang'))

    result = get_next_product(campaign)

    if result is None:
        response['status'] = "no_prediction_left"
        return jsonify(response)

    task, product = result
    task.set_attribution(session_id=session_id)
    response['product'] = parse_product_json(product, lang)
    response['task_id'] = str(task.id)

    predicted_category_name = get_category_name(task.predicted_category,
                                                lang)
    response['prediction'] = {
        'confidence': task.confidence,
        'id': task.predicted_category,
        'name': predicted_category_name,
    }

    return jsonify(response)


@app.route('/api/v1/categories/annotate', methods=['POST'])
def api_submit_categories_annotation():
    session_id = request.form.get('session_id')

    response = {}

    if session_id is None:
        session_id = generate_session_id()
        response['session_id'] = session_id

    task_id = request.form.get('task_id')

    if task_id is None:
        response['error'] = "invalid_task_id"
        response['error_description'] = "The task_id parameter is required"
        r = jsonify(response)
        r.status_code = 404
        return r

    try:
        annotation = int(request.form.get('annotation'))
    except TypeError:
        response['error'] = "invalid_annotation"
        response['error_description'] = "The annotation parameter (in -1, 0, 1) is required"
        r = jsonify(response)
        r.status_code = 404
        return r

    save_annotation(task_id, annotation, session_id)
    response['status'] = 'saved'
    return jsonify(response)


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
