from typing import Dict
from unittest.mock import ANY, call

import pytest

from robotoff.cli.main import categorize, init_elasticsearch


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


class MockResponse:
    def __init__(self, prediction: Dict):
        self.prediction = prediction

    def raise_for_status(self):
        pass

    def json(self) -> Dict:
        return self.prediction


def _construct_prediction_resp(category: str, conf: float) -> MockResponse:
    return MockResponse(
        prediction={
            "predictions": [
                {"output_mapper_layer": [conf], "output_mapper_layer_1": [category]},
            ]
        }
    )


def test_categorize_no_product(mocker, capsys):
    mocker.patch("robotoff.products.get_product", return_value=None)

    categorize("123")
    captured = capsys.readouterr()

    assert captured.out.startswith("Product 123 not found")


@pytest.mark.parametrize(
    "confidence,want_nothing",
    [
        (0.8, False),
        (0.3, True),
    ],
)
def test_categorize(mocker, capsys, confidence, want_nothing):
    mocker.patch(
        "robotoff.products.get_product",
        return_value={"product_name": "Test Product", "ingredients_tags": []},
    )
    mocker.patch(
        "robotoff.ml.category.neural.category_classifier.http_session.post",
        return_value=_construct_prediction_resp("en:chicken", confidence),
    )

    categorize("123")
    captured = capsys.readouterr()

    assert captured.out.startswith("Nothing predicted") == want_nothing
