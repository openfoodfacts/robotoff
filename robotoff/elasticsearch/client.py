import elasticsearch

from robotoff import settings


def get_es_client() -> elasticsearch.Elasticsearch:
    return elasticsearch.Elasticsearch(
        f"http://{settings.ELASTIC_USER}:{settings.ELASTIC_PASSWORD}@{settings.ELASTIC_HOST}:9200"
    )
