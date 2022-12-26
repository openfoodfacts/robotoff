from typing import Iterator

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from robotoff.elasticsearch.product.dump import generate_product_data
from robotoff.types import ElasticSearchIndex
from robotoff.utils import get_logger

logger = get_logger(__name__)

ES_INDEX_CONFIGS: dict[ElasticSearchIndex, dict] = {
    ElasticSearchIndex.product: {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "trigram": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "shingle"],
                    },
                    "reverse": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "reverse"],
                    },
                },
                "filter": {
                    "shingle": {
                        "type": "shingle",
                        "min_shingle_size": 2,
                        "max_shingle_size": 3,
                    }
                },
            },
        },
        "mappings": {
            "properties": {
                "ingredients_text_fr": {
                    "type": "text",
                    "fields": {
                        "trigram": {"type": "text", "analyzer": "trigram"},
                        "reverse": {"type": "text", "analyzer": "reverse"},
                    },
                },
                "code": {"type": "keyword"},
            }
        },
    },
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
            }
        },
    },
}


class ElasticsearchExporter:
    """ElasticsearchExporter exports new index data to Elasticsearch."""

    def __init__(self, es_client: Elasticsearch):
        self.es_client = es_client

    def _get_product_data(self) -> Iterator[dict]:
        for barcode, item in generate_product_data():
            yield {
                "_id": barcode,
                "_index": ElasticSearchIndex.product.value,
                **item,
            }

    def load_index(self, index: ElasticSearchIndex) -> None:
        """Creates the given index if it doesn't already exist."""
        if not self.es_client.indices.exists(index=index):
            logger.info("Creating index: %s", index)
            self.es_client.indices.create(index=index, **ES_INDEX_CONFIGS[index])

    def load_all_indices(self) -> None:
        """Create all ES indices if they do not already exist."""
        for index in ES_INDEX_CONFIGS:
            self.load_index(index)

    def export_index_data(self) -> None:
        """Given the index to export data for, this function removes existing data and exports a newer version.

        .. warning: right now, we delete then recreate the index.
           This means that as this method runs,
           some request might be silently handled erroneously (with a partial index).
           This is not a problem right now, as we don't have *real-time* requests,
           but only async ones for categories.
        """
        logger.info("Deleting existing product data...")
        resp = self.es_client.delete_by_query(
            query={"match_all": {}},
            index=ElasticSearchIndex.product.value,
            ignore_unavailable=True,
        )
        logger.info("Deleted %d documents from product", resp["deleted"])
        logger.info("Starting product export to Elasticsearch...")
        bulk(self.es_client, self._get_product_data())
