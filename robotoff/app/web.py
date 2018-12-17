import logging

from flask import Flask, request, render_template, session

from robotoff.app.core import (generate_session_id,
                               get_next_product,
                               normalize_lang,
                               parse_product_json,
                               get_category_name,
                               save_annotation)

app = Flask(__name__)

app.secret_key = b'k@\xcf\xb0\xfb\x94\xb2=3cJ7Q\xf1F\xd5'


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


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
