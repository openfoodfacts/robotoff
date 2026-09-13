import peewee
import pytest

from robotoff.app.core import get_insights


@pytest.fixture
def insight_store(monkeypatch):
    """Exercise insight filtering against a small in-memory SQL table."""
    test_db = peewee.SqliteDatabase(":memory:")

    class Insight(peewee.Model):
        barcode = peewee.TextField()
        type = peewee.TextField()
        value_tag = peewee.TextField()
        server_type = peewee.TextField(default="off")
        annotation = peewee.IntegerField(null=True)

        class Meta:
            database = test_db

    monkeypatch.setattr("robotoff.app.core.ProductInsight", Insight)
    with test_db:
        test_db.create_tables([Insight])
        Insight.insert_many(
            [
                {"barcode": "1", "type": "brand", "value_tag": "nestle"},
                {"barcode": "2", "type": "brand", "value_tag": "xx:nestle"},
                {"barcode": "3", "type": "label", "value_tag": "nestle"},
                {"barcode": "4", "type": "label", "value_tag": "xx:nestle"},
                {"barcode": "5", "type": "brand", "value_tag": "en:nestle"},
                {"barcode": "6", "type": "brand", "value_tag": "carrefour"},
            ]
        ).execute()
        Insight.create(barcode="7", type="brand", value_tag="nestle", server_type="obf")
        Insight.create(barcode="8", type="brand", value_tag="xx:nestle", annotation=1)
        yield


@pytest.mark.parametrize(
    "value_tag,keep_types,expected",
    [
        ("xx:nestle", ["brand"], {"1", "2"}),
        ("nestle", ["brand"], {"1", "2"}),
        ("xx:nestle", None, {"1", "2", "4"}),
        ("nestle", None, {"1", "2", "3"}),
        ("xx:nestle", ["brand", "label"], {"1", "2", "4"}),
        ("xx:nestle", ["label"], {"4"}),
        ("nestle", ["label"], {"3"}),
        ("en:nestle", ["brand"], {"5"}),
        ("xx:missing", ["brand"], set()),
        ("xx:nestle", [], set()),
    ],
)
def test_get_insights_brand_value_tag(insight_store, value_tag, keep_types, expected):
    filters = {"value_tag": value_tag, "keep_types": keep_types}
    results = list(get_insights(**filters))
    assert {insight.barcode for insight in results} == expected
    assert get_insights(**filters, count=True) == len(expected)
    assert get_insights(**filters, count=True, max_count=1) == min(1, len(expected))


def test_get_insights_brand_value_tag_pagination(insight_store):
    filters = {"value_tag": "xx:nestle", "keep_types": ["brand"]}
    assert len(list(get_insights(**filters, limit=1))) == 1
    assert list(get_insights(**filters, limit=1, offset=2)) == []
