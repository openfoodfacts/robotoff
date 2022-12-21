import json
from typing import Iterable

from elasticsearch import Elasticsearch

from robotoff import settings
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

    def _delete_existing_data(self, index: ElasticSearchIndex) -> None:
        resp = self.es_client.delete_by_query(
            query={"match_all": {}},
            index=index,
            ignore_unavailable=True,
        )

        logger.info("Deleted %d documents from %s", resp["deleted"], index)

    def _get_data(self, index: ElasticSearchIndex) -> Iterable[tuple[str, dict]]:
        if index == ElasticSearchIndex.product:
            return generate_product_data()

        raise ValueError(f"unknown index: {index}")

    def load_index(self, index: ElasticSearchIndex) -> None:
        """Creates the given index if it doesn't already exist."""
        if not self.es_client.indices.exists(index=index):
            logger.info("Creating index: %s", index)
            self.es_client.indices.create(index=index, **ES_INDEX_CONFIGS[index])

    def load_all_indices(self) -> None:
        """Create all ES indices if they do not already exist."""
        for index in ES_INDEX_CONFIGS:
            self.load_index(index)

    def export_index_data(self, index: ElasticSearchIndex) -> int:
        """Given the index to export data for, this function removes existing data and exports a newer version.

        .. warning: right now, we delete then recreate the index.
           This means that as this method runs,
           some request might be silently handled erroneously (with a partial index).
           This is not a problem right now, as we don't have *real-time* requests,
           but only async ones for categories.

        Returns the number of rows inserted into the index."""
        logger.info("Deleting existing %s data...", index)
        self._delete_existing_data(index)
        index_data = self._get_data(index)

        logger.info("Starting %s export to Elasticsearch...", index)
        rows_inserted = perform_export(self.es_client, index_data, index)

        logger.info("Inserted %d rows for index %s", rows_inserted, index)
        return rows_inserted


def perform_export(
    client, data: Iterable[tuple[str, dict]], index: str, batch_size=100
) -> int:
    batch = []
    rows_inserted = 0

    for id_, item in data:
        batch.append(({"index": {"_id": id_}}, item))

        if len(batch) >= batch_size:
            insert_batch(client, batch, index)
            rows_inserted += len(batch)
            batch = []

    if batch:
        insert_batch(client, batch, index)
        rows_inserted += len(batch)

    return rows_inserted


def insert_batch(client, batch: Iterable[tuple[dict, dict]], index: str):
    body = ""
    for action, source in batch:
        body += "{}\n{}\n".format(json.dumps(action), json.dumps(source))

    client.bulk(body=body, index=index, doc_type=settings.ELASTICSEARCH_TYPE)
