from typing import List

from elasticsearch import Elasticsearch
from robotoff import settings
from robotoff.elasticsearch.category.dump import generate_category_data
from robotoff.elasticsearch.product.dump import product_export
from robotoff.utils import get_logger
from robotoff.utils.es import perform_export

logger = get_logger()


class ElasticsearchExporter(object):
    """ElasticsearchExporter exports new index data to Elasticsearch. """

    def __init__(self, es_client: Elasticsearch):
        self.es_client = es_client

    def _delete_existing_data(self, index: str):
        resp = self.es_client.delete_by_query(
            body={"query": {"match_all": {}}},
            index=index,
            doc_type=settings.ELASTICSEARCH_TYPE,
            ignore_unavailable=True,
        )

        logger.info("Deleted {} documents from {}".format(resp["deleted"], index))

    def export_index_data(self, index: str):
        """Given the index to export data for, this function removes existing data and exports a newer version."""
        logger.info("Deleting existing {} data...".format(index))
        self._delete_existing_data(index)

        if index == settings.ElasticsearchIndex.CATEGORY:
            index_data = generate_category_data()
        elif index == settings.ElasticsearchIndex.PRODUCT:
            index_data = product_export()
        else:
            raise ValueError("unknown index: {}".format(index))

        logger.info("Starting {} export to Elasticsearch...".format(index))

        rows_inserted = perform_export(self.es_client, index_data, index)

        logger.info("{} rows inserted for index {}", rows_inserted, index)
