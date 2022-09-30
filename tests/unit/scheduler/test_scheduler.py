from unittest.mock import ANY, call

from robotoff import scheduler


def test_update_data(mocker):
    exporter = mocker.MagicMock()

    # TODO: test the download_product_dataset body.
    mocker.patch("robotoff.scheduler._download_product_dataset")
    mocker.patch("robotoff.scheduler.ElasticsearchExporter", return_value=exporter)

    scheduler._update_data()

    exporter.load_index.assert_has_calls([call("product", ANY)])
    exporter.export_index_data.assert_has_calls([call("product")])
