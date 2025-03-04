from elasticsearch import Elasticsearch

from robotoff import settings
from robotoff.types import ElasticSearchIndex
from robotoff.utils import get_logger

logger = get_logger(__name__)


def get_es_client() -> Elasticsearch:
    return Elasticsearch(
        f"http://{settings.ELASTIC_USER}:{settings.ELASTIC_PASSWORD}@{settings.ELASTIC_HOST}:9200",
        request_timeout=20,  # we might have long running queries
    )


ES_INDEX_CONFIGS: dict[ElasticSearchIndex, dict] = {
    ElasticSearchIndex.logo: {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "dense_vector",
                    "dims": 512,
                    "index": True,
                    "similarity": "dot_product",
                    "index_options": {"type": "hnsw", "m": 16, "ef_construction": 100},
                },
                "server_type": {"type": "keyword"},
            },
        },
    },
}


class ElasticsearchExporter:
    """ElasticsearchExporter exports new index data to Elasticsearch."""

    def __init__(self, es_client: Elasticsearch):
        self.es_client = es_client

    def load_index(self, index: ElasticSearchIndex) -> None:
        """Creates the given index if it doesn't already exist."""
        if not self.es_client.indices.exists(index=index):
            logger.info("Creating index: %s", index)
            self.es_client.indices.create(index=index, **ES_INDEX_CONFIGS[index])

    def load_all_indices(self) -> None:
        """Create all ES indices if they do not already exist."""
        for index in ES_INDEX_CONFIGS:
            self.load_index(index)
