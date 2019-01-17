import abc

import requests
from robotoff.models import ProductInsight
from robotoff.utils import get_logger

logger = get_logger(__name__)


AUTH = ("roboto-app", "4mbN9wJp8LBShcH")
POST_URL = "https://world.openfoodfacts.org/cgi/product_jqm2.pl"
http_session = requests.Session()


class InsightAnnotator(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def annotate(self, insight: ProductInsight):
        pass


class PackagerCodeAnnotator(InsightAnnotator):
    def annotate(self, insight: ProductInsight):
        emb_code = insight.data['text']
        self.send_request(insight.barcode, emb_code)

    @staticmethod
    def send_request(barcode: str, emb_code: str):
        params = {
            'code': barcode,
            'add_emb_codes': emb_code,
            'user_id': AUTH[0],
            'password': AUTH[1],
        }

        r = http_session.get(POST_URL, params=params)
        r.raise_for_status()
        json = r.json()

        status = json.get('status_verbose')

        if status != "fields saved":
            logger.warn(
                "Unexpected status during product update: {}".format(
                    status))


class InsightAnnotatorFactory:
    mapping = {
        'packager_code': PackagerCodeAnnotator,
    }

    @classmethod
    def create(cls, identifier: str) -> InsightAnnotator:
        if identifier not in cls.mapping:
            raise ValueError("unknown annotator: {}".format(identifier))

        return cls.mapping[identifier]()
