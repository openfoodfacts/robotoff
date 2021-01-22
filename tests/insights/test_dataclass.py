import pytest

from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import ProductInsights, RawInsight


def test_product_insights_merge():
    insights_1 = [RawInsight(type=InsightType.label, data={}, value_tag="en:organic")]
    product_insights_1 = ProductInsights(
        insights=insights_1,
        barcode="123",
        type=InsightType.label,
        source_image="/123/1.jpg",
    )

    insights_2 = [RawInsight(type=InsightType.label, data={}, value_tag="en:pgi")]
    product_insights_2 = ProductInsights(
        insights=insights_2,
        barcode="123",
        type=InsightType.label,
        source_image="/123/1.jpg",
    )

    merged_product_insights = ProductInsights.merge(
        [product_insights_1, product_insights_2]
    )

    assert merged_product_insights.type == InsightType.label
    assert merged_product_insights.barcode == "123"
    assert merged_product_insights.source_image == "/123/1.jpg"
    assert merged_product_insights.insights == insights_1 + insights_2


def test_product_insights_failed_merge():
    with pytest.raises(ValueError):
        ProductInsights.merge([])

    with pytest.raises(ValueError):
        ProductInsights.merge(
            [
                ProductInsights(
                    insights=[],
                    barcode="123",
                    type=InsightType.label,
                    source_image="/123/1.jpg",
                ),
                ProductInsights(
                    insights=[],
                    barcode="234",
                    type=InsightType.label,
                    source_image="/123/1.jpg",
                ),
            ]
        )

    with pytest.raises(ValueError):
        ProductInsights.merge(
            [
                ProductInsights(
                    insights=[],
                    barcode="123",
                    type=InsightType.label,
                    source_image="/123/1.jpg",
                ),
                ProductInsights(
                    insights=[],
                    barcode="123",
                    type=InsightType.category,
                    source_image="/123/1.jpg",
                ),
            ]
        )

    with pytest.raises(ValueError):
        ProductInsights.merge(
            [
                ProductInsights(
                    insights=[],
                    barcode="123",
                    type=InsightType.label,
                    source_image="/123/1.jpg",
                ),
                ProductInsights(
                    insights=[],
                    barcode="123",
                    type=InsightType.label,
                    source_image="/123/2.jpg",
                ),
            ]
        )

    with pytest.raises(ValueError):
        ProductInsights.merge(
            [
                ProductInsights(
                    insights=[],
                    barcode="123",
                    type=InsightType.label,
                    source_image="/123/1.jpg",
                ),
                ProductInsights(
                    insights=[],
                    barcode="123",
                    type=InsightType.category,
                    source_image="/123/2.jpg",
                ),
            ]
        )
