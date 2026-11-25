import pytest

from robotoff.brands import get_brand_prefix, in_barcode_range, normalize_brand_tag
from robotoff.insights.importer import BrandInsightImporter
from robotoff.models import ProductInsight
from robotoff.types import Prediction, PredictionType


@pytest.mark.parametrize(
    "barcode,brand_tag,is_valid",
    [
        ("5400141651306", "boni", True),
        ("5400142968395", "boni", False),
        ("3406790524499", "boni", False),
        ("3406790524499", "unknown-brand", False),
        ("3660523327656", "jeff-de-bruges", True),
        ("2968248002546", "thomas", False),
        ("3350240540277", "maison-prunier", True),
    ],
)
def test_in_barcode_range(barcode, brand_tag, is_valid):
    brand_prefix = get_brand_prefix()
    assert in_barcode_range(brand_prefix, brand_tag, barcode) is is_valid


@pytest.mark.parametrize(
    "tag,expected",
    [
        ("nestle", "xx:nestle"),
        ("xx:nestle", "xx:nestle"),
        (None, None),
        ("", ""),
        ("en:nestle", "en:nestle"),
        ("xx:", "xx:"),
    ],
)
def test_normalize_brand_tag(tag, expected):
    assert normalize_brand_tag(tag) == expected
    assert normalize_brand_tag(expected) == expected


@pytest.mark.parametrize("resource_tag", ["nestle", "xx:nestle"])
@pytest.mark.parametrize("tag", ["nestle", "xx:nestle"])
def test_brand_validation_accepts_both_resource_formats(mocker, resource_tag, tag):
    mocker.patch("robotoff.insights.importer.get_brand_blacklist", return_value=set())
    mocker.patch(
        "robotoff.insights.importer.get_brand_prefix",
        return_value={(resource_tag, "1234567xxxxxx")},
    )
    prediction = Prediction(
        type=PredictionType.brand,
        value_tag=tag,
        predictor="taxonomy",
        barcode="1234567891234",
    )
    assert BrandInsightImporter.is_prediction_valid(prediction)
    prediction.barcode = "9876543211234"
    assert not BrandInsightImporter.is_prediction_valid(prediction)


@pytest.mark.parametrize("blacklist_tag", ["nestle", "xx:nestle"])
@pytest.mark.parametrize("tag", ["nestle", "xx:nestle"])
def test_brand_blacklist_cannot_be_bypassed_by_prefix(mocker, blacklist_tag, tag):
    mocker.patch(
        "robotoff.insights.importer.get_brand_blacklist", return_value={blacklist_tag}
    )
    assert not BrandInsightImporter.is_prediction_valid(
        Prediction(
            type=PredictionType.brand,
            value_tag=tag,
            predictor="taxonomy",
            barcode="123",
        )
    )


def test_brand_conflict_treats_legacy_and_canonical_tags_as_equal():
    assert BrandInsightImporter.is_conflicting_insight(
        ProductInsight(value_tag="nestle"), ProductInsight(value_tag="xx:nestle")
    )
    assert not BrandInsightImporter.is_conflicting_insight(
        ProductInsight(value_tag="en:nestle"), ProductInsight(value_tag="xx:nestle")
    )
