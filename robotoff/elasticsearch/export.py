from typing import List

import orjson
from elasticsearch import Elasticsearch

from robotoff import settings
from robotoff.elasticsearch.category.dump import generate_category_data
from robotoff.elasticsearch.product.dump import generate_product_data
from robotoff.utils import get_logger
from robotoff.utils.es import perform_export

logger = get_logger()


class ElasticsearchExporter(object):
    """ElasticsearchExporter exports new index data to Elasticsearch. """

    def __init__(self, es_client: Elasticsearch):
        self.es_client = es_client

    def _delete_existing_data(self, index: str) -> None:
        resp = self.es_client.delete_by_query(
            body={"query": {"match_all": {}}},
            index=index,
            doc_type=settings.ELASTICSEARCH_TYPE,
            ignore_unavailable=True,
        )

        logger.info("Deleted {} documents from {}".format(resp["deleted"], index))

    def load_index(self, index: str, index_filepath: str) -> None:
        """ Creates the given index if it doesn't already exist."""
        if not self.es_client.indices.exists(index):
            logger.info("Creating index: {}".format(index))
            with open(index_filepath, "rb") as f:
                conf = orjson.loads(f.read())
            self.es_client.indices.create(index=index, body=conf)

    def export_index_data(self, index: str) -> int:
        """Given the index to export data for, this function removes existing data and exports a newer version.
        Returns the number of rows inserted into the index."""
        logger.info("Deleting existing {} data...".format(index))
        self._delete_existing_data(index)

        if index == settings.ElasticsearchIndex.CATEGORY:
            index_data = generate_category_data()
        elif index == settings.ElasticsearchIndex.PRODUCT:
            index_data = generate_product_data()
        else:
            raise ValueError("unknown index: {}".format(index))

        logger.info("Starting {} export to Elasticsearch...".format(index))

        rows_inserted = perform_export(self.es_client, index_data, index)

        logger.info("{} rows inserted for index {}".format(rows_inserted, index))
        return rows_inserted
