import pytest

from robotoff.elasticsearch import get_es_client
from robotoff.elasticsearch.export import ElasticsearchExporter
from robotoff.types import ElasticSearchIndex


def test_export_index_data_unsupported(mocker):
    fake_client = mocker.MagicMock()

    exporter = ElasticsearchExporter(fake_client)
    with pytest.raises(ValueError):
        exporter.export_index_data("i-dont-exist")


def test_load_index_already_exists(mocker):
    mocker.patch("elasticsearch.client.IndicesClient.exists", return_value=True)
    create_call = mocker.patch("elasticsearch.client.IndicesClient.create")

    exporter = ElasticsearchExporter(get_es_client())
    exporter.load_index(ElasticSearchIndex.product)
    create_call.assert_not_called()


def test_load_index(mocker):
    mocker.patch("elasticsearch.client.IndicesClient.exists", return_value=False)
    create_call = mocker.patch("elasticsearch.client.IndicesClient.create")

    exporter = ElasticsearchExporter(get_es_client())
    exporter.load_index(ElasticSearchIndex.product)
    create_call.assert_called_once()
