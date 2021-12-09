from unittest.mock import ANY, call

import pytest

from robotoff.cli.main import init_elasticsearch


@pytest.mark.parametrize(
    "load_index,load_data,to_load,index_loads_calls,data_loads_calls",
    [
        (False, False, [], [], []),
        (False, True, ["non-existent"], [], []),
        (False, True, ["category"], [], [call("category")]),
        (
            True,
            True,
            ["product", "category"],
            [call("product", ANY), call("category", ANY)],
            [call("product"), call("category")],
        ),
    ],
)
def test_init_elasticsearch(
    mocker, load_index, load_data, to_load, index_loads_calls, data_loads_calls
):
    fake_exporter = mocker.MagicMock()

    mocker.patch(
        "robotoff.elasticsearch.export.ElasticsearchExporter",
        return_value=fake_exporter,
    )

    init_elasticsearch(load_index, load_data, to_load)

    fake_exporter.load_index.assert_has_calls(index_loads_calls)
    fake_exporter.export_index_data.assert_has_calls(data_loads_calls)
