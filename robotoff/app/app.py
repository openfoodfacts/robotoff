import uuid

import peewee
from flask import Flask, request, render_template, session
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


def set_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())


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


def get_category_name(identifier, best_language):
    if identifier not in category_json:
        return identifier

    category = category_json[identifier]
    category_names = category['name']

    if 'fr' in category_names and best_language in ('fr', 'fr-FR'):
        return category_names['fr']

    if 'en' in category_names:
        return category_names['en']

    return identifier


def parse_product_json(data):
    return {
        'image_url': data.get('image_front_url'),
        'ingredients_texts': data.get('ingredients_text'),
        'product_name': data.get('product_name'),
        'brands': data.get('brands'),
        'categories_tags': list(set(data.get('categories_tags', []))),
        'product_link': "https://world.openfoodfacts.org/product/{}".format(data.get('code')),
    }


def render_next_product(campaign: str=None):
    while True:
        query = (CategorizationTask.select()
                                   .where(CategorizationTask.attributed_at
                                          .is_null()))

        if campaign is not None:
            query = query.where(CategorizationTask.campaign ==
                                campaign).order_by(peewee.fn.Random())
        else:
            query = query.order_by(CategorizationTask.category_depth.desc())

        random_task_list = list(query.limit(1))

        if not random_task_list:
            return render_template("index.html", no_product=True)

        random_task = random_task_list[0]
        product = get_product(random_task.product_id)

        # Product may be None if not found
        if product and random_task.last_updated_at == str(product['last_modified_t']):
            break
        else:
            random_task.outdated = True
            random_task.save()
            app.logger.info("Product modified since prediction, fetching a "
                            "new product from DB...")

    random_task.set_attribution(session_id=get_session_id())
    context = parse_product_json(product)
    context['task_id'] = str(random_task.id)
    context['confidence'] = random_task.confidence
    predicted_category_name = get_category_name(random_task.predicted_category,
                                                request.accept_languages.best)
    context['predicted_category_name'] = predicted_category_name
    context['predicted_category'] = random_task.predicted_category
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
def main():
    set_session_id()
    return render_next_product()


@app.route('/campaign/<campaign>')
def main(campaign):
    set_session_id()
    return render_next_product(campaign)


@app.route('/', methods=['POST'])
@app.route('/campaign/<campaign>', method=['POST'])
def categorize(campaign=None):
    set_session_id()
    task_id = request.form['task_id']
    annotation = int(request.form['annotation'])
    session_id = get_session_id()

    try:
        task = CategorizationTask.get_by_id(task_id)
    except CategorizationTask.DoesNotExist:
        task = None

    if (not task or
            task.attributed_to_session_id != session_id or
            task.annotation is not None):
        return render_next_product(campaign)

    task.annotation = annotation
    task.save()

    if annotation == 1:
        current_categories = request.form['current_categories'].split(',')
        current_categories.append(task.predicted_category)
        save_categories(task.product_id, current_categories)

    task.set_completion(session_id=session_id)
    return render_next_product(campaign)
