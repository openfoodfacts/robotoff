from pathlib import Path
from typing import Dict, Iterable, Tuple

import orjson
from elasticsearch import Elasticsearch

from robotoff import settings
from robotoff.elasticsearch.category.dump import generate_category_data
from robotoff.elasticsearch.product.dump import generate_product_data
from robotoff.utils import get_logger
from robotoff.utils.es import perform_export

logger = get_logger(__name__)


class ElasticsearchExporter:
    """ElasticsearchExporter exports new index data to Elasticsearch."""

    def __init__(self, es_client: Elasticsearch):
        self.es_client = es_client

    def _delete_existing_data(self, index: str) -> None:
        resp = self.es_client.delete_by_query(
            body={"query": {"match_all": {}}},
            index=index,
            ignore_unavailable=True,
            doc_type=settings.ELASTICSEARCH_TYPE,
        )

        logger.info(f"Deleted %d documents from {index}", resp["deleted"])

    def _get_data(self, index: str) -> Iterable[Tuple[str, Dict]]:
        if index == settings.ElasticsearchIndex.CATEGORY:
            return generate_category_data()

        if index == settings.ElasticsearchIndex.PRODUCT:
            return generate_product_data()

        raise ValueError(f"unknown index: {index}")

    def load_index(self, index: str, index_filepath: Path) -> None:
        """Creates the given index if it doesn't already exist."""
        if not self.es_client.indices.exists(index=index):
            logger.info(f"Creating index: {index}")
            with open(index_filepath, "rb") as f:
                conf = orjson.loads(f.read())
            self.es_client.indices.create(index=index, body=conf)

    def export_index_data(self, index: str) -> int:
        """Given the index to export data for, this function removes existing data and exports a newer version.

        .. warning: right now, we delete then recreate the index.
           This means that as this method runs,
           some request might be silently handled erroneously (with a partial index).
           This is not a problem right now, as we don't have *real-time* requests,
           but only async ones for categories.

        Returns the number of rows inserted into the index."""
        logger.info(f"Deleting existing {index} data...")
        self._delete_existing_data(index)

        index_data = self._get_data(index)

        logger.info(f"Starting {index} export to Elasticsearch...")

        rows_inserted = perform_export(self.es_client, index_data, index)

        logger.info(f"Inserted %d rows for index {index}", rows_inserted)
        return rows_inserted
