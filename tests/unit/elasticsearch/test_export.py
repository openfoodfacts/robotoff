from unittest.mock import patch

import pytest

from robotoff.elasticsearch.export import ElasticsearchExporter
from robotoff.taxonomy import Taxonomy
from robotoff.utils.es import get_es_client


def test_export_index_data_unsupported(mocker):
    fake_client = mocker.MagicMock()

    exporter = ElasticsearchExporter(fake_client)
    with pytest.raises(ValueError):
        exporter.export_index_data("i-dont-exist")


def _category_taxonomy() -> Taxonomy:
    return Taxonomy.from_dict({"en:mushrooms": {"lang": "fr"}})


def test_export_category_index_data(mocker):
    del_by_query = mocker.patch(
        "robotoff.elasticsearch.export.Elasticsearch.delete_by_query",
        return_value={"deleted": 10},
    )
    bulk_insert = mocker.patch("robotoff.utils.es.elasticsearch.Elasticsearch.bulk")
    mocker.patch(
        "robotoff.elasticsearch.category.dump.get_taxonomy",
        return_value=_category_taxonomy(),
    )

    exporter = ElasticsearchExporter(get_es_client())
    inserted = exporter.export_index_data("category")

    del_by_query.assert_called_once()
    bulk_insert.assert_called_once()
    assert inserted == 1


def test_load_index_already_exists(mocker):
    mocker.patch("elasticsearch.client.IndicesClient.exists", return_value=True)
    create_call = mocker.patch("elasticsearch.client.IndicesClient.create")

    exporter = ElasticsearchExporter(get_es_client())
    exporter.load_index("category", "filepath/")

    create_call.assert_not_called()


def test_load_index(mocker):
    mocker.patch("elasticsearch.client.IndicesClient.exists", return_value=False)
    create_call = mocker.patch("elasticsearch.client.IndicesClient.create")

    exporter = ElasticsearchExporter(get_es_client())

    with patch("builtins.open", mocker.mock_open(read_data='{"a":"b"}')):
        exporter.load_index("category", "filepath/")

    create_call.assert_called_once()
