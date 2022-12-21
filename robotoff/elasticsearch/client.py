import elasticsearch

from robotoff import settings


def get_es_client():
    return elasticsearch.Elasticsearch(settings.ELASTICSEARCH_HOSTS)
