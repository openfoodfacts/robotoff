from unittest.mock import MagicMock, patch

import pytest
from elasticsearch import Elasticsearch
from elasticsearch.helpers import BulkIndexError

from robotoff.logos import compute_iou, delete_ann_logos, generate_prediction
from robotoff.types import ElasticSearchIndex, Prediction, PredictionType, ServerType


@pytest.mark.parametrize(
    "box_1,box_2,expected_iou",
    [
        ((0.0, 0.0, 0.1, 0.1), (0.2, 0.2, 0.4, 0.4), 0.0),
        ((0.1, 0.1, 0.5, 0.5), (0.1, 0.1, 0.5, 0.5), 1.0),
        ((0.1, 0.1, 0.5, 0.5), (0.2, 0.2, 0.6, 0.6), (0.3 * 0.3) / (0.16 * 2 - 0.09)),
        ((0.2, 0.2, 0.6, 0.6), (0.1, 0.1, 0.5, 0.5), (0.3 * 0.3) / (0.16 * 2 - 0.09)),
    ],
)
def test_compute_iou(box_1, box_2, expected_iou):
    assert compute_iou(box_1, box_2) == expected_iou


@pytest.mark.parametrize(
    "logo_type,logo_value,data,automatic_processing,confidence,prediction",
    [
        ("category", "en:breads", {}, 0.1, False, None),
        ("label", None, {}, 0.1, False, None),
        (
            "label",
            "en:eu-organic",
            {},
            False,
            0.8,
            Prediction(
                type=PredictionType.label,
                data={},
                value_tag="en:eu-organic",
                value=None,
                automatic_processing=False,
                predictor="universal-logo-detector",
                confidence=0.8,
            ),
        ),
        (
            "brand",
            "Carrefour",
            {},
            False,
            0.5,
            Prediction(
                type=PredictionType.brand,
                data={},
                value_tag="carrefour",
                value="Carrefour",
                automatic_processing=False,
                predictor="universal-logo-detector",
                confidence=0.5,
            ),
        ),
    ],
)
def test_generate_prediction(
    logo_type, logo_value, data, automatic_processing, confidence, prediction
):
    assert (
        generate_prediction(
            logo_type,
            logo_value,
            data,
            confidence,
            ServerType.off,
            automatic_processing,
        )
        == prediction
    )


@patch("robotoff.logos.elasticsearch_bulk")
def test_delete_ann_logos(mock_bulk):
    es_client = MagicMock(spec=Elasticsearch)
    logo_ids = [1, 2, 3]
    actions = [
        {
            "_op_type": "delete",
            "_index": ElasticSearchIndex.logo.name,
            "_id": logo_id,
        }
        for logo_id in logo_ids
    ]
    mock_bulk.return_value = (len(logo_ids), [])
    assert delete_ann_logos(es_client, logo_ids) == len(logo_ids)
    mock_bulk.assert_called_once()
    call = mock_bulk.mock_calls[0]
    assert call.args[0] == es_client
    assert list(call.args[1]) == actions

    mock_bulk.reset_mock()
    mock_bulk.side_effect = BulkIndexError("error", ["error1"])

    with pytest.raises(BulkIndexError):
        count = delete_ann_logos(es_client, logo_ids)
        assert count == 0

    call = mock_bulk.mock_calls[0]
    assert call.args[0] == es_client
    assert list(call.args[1]) == actions
