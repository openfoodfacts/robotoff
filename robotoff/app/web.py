import logging

from flask import Flask, request, render_template, session, jsonify
from flask_cors import CORS

from robotoff.app.core import (generate_session_id,
                               get_next_product,
                               normalize_lang,
                               parse_product_json,
                               get_category_name,
                               save_annotation)

app = Flask(__name__)
CORS(app)

app.secret_key = b'k@\xcf\xb0\xfb\x94\xb2=3cJ7Q\xf1F\xd5'


# Webapp

def set_session_id():
    if 'session_id' not in session:
        session['session_id'] = generate_session_id()


def get_session_id():
    return session['session_id']


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


@app.route('/')
@app.route('/campaign/<campaign>')
def categorize_get(campaign=None):
    set_session_id()
    return render_next_product(campaign)


@app.route('/', methods=['POST'])
@app.route('/campaign/<campaign>', methods=['POST'])
def categorize_post(campaign=None):
    set_session_id()
    task_id = request.form['task_id']
    annotation = int(request.form['annotation'])
    save_annotation(task_id, annotation)
    return render_next_product(campaign)


# API

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
    response = {}
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

    save = request.form.get('save')
    try:
        if save is not None:
            save = int(save)
    except TypeError:
        response['error'] = "invalid_save"
        response['error_description'] = "The save parameter must be 1 or 0"
        r = jsonify(response)
        r.status_code = 404
        return r

    if save is None:
        save = True

    save_annotation(task_id, annotation, save=save)
    response['status'] = 'saved'
    return jsonify(response)


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
