from robotoff.cli.main import init_elasticsearch


def test_init_elasticsearch(mocker):
    fake_exporter = mocker.MagicMock()

    mocker.patch(
        "robotoff.elasticsearch.ElasticsearchExporter",
        return_value=fake_exporter,
    )

    init_elasticsearch()
    fake_exporter.load_all_indices.assert_has_calls([])
