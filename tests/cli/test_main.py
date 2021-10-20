import pytest

from robotoff.cli.main import _init_elasticsearch_impl
from robotoff.elasticsearch.export import ElasticsearchExporter


class FakeESExporter(ElasticsearchExporter):
    def __init__(self):
        self.index_loads = 0
        self.data_loads = 0

    def load_index(self, *_):
        self.index_loads += 1

    def export_index_data(self, *_):
        self.data_loads += 1


@pytest.mark.parametrize(
    "load_index,load_data,to_load,want_index_loads,want_data_loads",
    [
        (False, False, [], 0, 0),
        (False, True, ["non-existent"], 0, 0),
        (False, True, ["category"], 0, 1),
        (True, True, ["product", "category"], 2, 2),
    ],
)
def test_init_elasticsearch(
    load_index, load_data, to_load, want_index_loads, want_data_loads
):
    f = FakeESExporter()

    _init_elasticsearch_impl(f, load_index, load_data, to_load)

    assert (f.index_loads, f.data_loads) == (want_index_loads, want_data_loads)
