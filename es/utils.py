import elasticsearch

ELASTIC_SEARCH_HOST = "localhost:9200"
ELASTIC_SEARCH_INDEX = "off"
ELASTIC_SEARCH_TYPE = "document"


def get_es_client():
    return elasticsearch.Elasticsearch(ELASTIC_SEARCH_HOST)
