import pytest

from robotoff.cli.main import categorize, init_elasticsearch
from robotoff.types import NeuralCategoryClassifierModel


def test_init_elasticsearch(mocker):
    fake_exporter = mocker.MagicMock()

    mocker.patch(
        "robotoff.elasticsearch.export.ElasticsearchExporter",
        return_value=fake_exporter,
    )

    init_elasticsearch(True)
    fake_exporter.load_all_indices.assert_has_calls([])
    fake_exporter.export_index_data.assert_has_calls([])


class MockResponse:
    def __init__(self, prediction: dict):
        self.prediction = prediction

    def raise_for_status(self):
        pass

    def json(self) -> dict:
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
    mocker.patch("robotoff.off.get_product", return_value=None)

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
        "robotoff.off.get_product",
        return_value={
            "product_name": "Test Product",
            "ingredients_tags": ["ingredient1"],
        },
    )
    mocker.patch(
        "robotoff.prediction.category.neural.category_classifier.keras_category_classifier_2_0.http_session.post",
        return_value=_construct_prediction_resp("en:chicken", confidence),
    )

    categorize("123", threshold=0.5, model_name=NeuralCategoryClassifierModel.keras_2_0)
    captured = capsys.readouterr()

    assert ("Nothing predicted" in captured.out) == want_nothing
