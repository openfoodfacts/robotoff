import requests

from robotoff import settings

http_session = requests.session()

TF_SERVING_BASE_URL = "http://{}:{}/v1/models".format(
    settings.TF_SERVING_HOST,
    settings.TF_SERVING_HTTP_PORT)
