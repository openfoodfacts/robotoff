import pytest

from robotoff.app.core import get_insights
from robotoff.types import ServerType

from ..models_utils import ProductInsightFactory, clean_db


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        # clean db
        clean_db()
        # Run the test case.
        yield
        clean_db()


def test_filter_by_language_codes():
    """Test that insights can be filtered by language_codes."""
    # Create insights with different language codes
    insight_fr = ProductInsightFactory(
        data={"lang": "fr"},
        server_type=ServerType.off.name,
    )
    insight_en = ProductInsightFactory(
        data={"lang": "en"},
        server_type=ServerType.off.name,
    )
    insight_de = ProductInsightFactory(
        data={"lang": "de"},
        server_type=ServerType.off.name,
    )
    insight_no_lang = ProductInsightFactory(
        data={},  # No language code
        server_type=ServerType.off.name,
    )
    insight_multi_lang = ProductInsightFactory(
        data={"languages": ["fr", "es", "it"]},
        server_type=ServerType.off.name,
    )

    # Test filtering by a single language code
    insights = list(
        get_insights(
            server_type=ServerType.off,
            language_codes=["fr"],
        )
    )
    assert len(insights) == 1
    assert insights[0].id == insight_fr.id

    # Test filtering by multiple language codes
    insights = list(
        get_insights(
            server_type=ServerType.off,
            language_codes=["fr", "en"],
        )
    )
    assert len(insights) == 2
    insight_ids = {insight.id for insight in insights}
    assert insight_ids == {insight_fr.id, insight_en.id}

    # Test filtering by a language code that doesn't exist
    insights = list(
        get_insights(
            server_type=ServerType.off,
            language_codes=["es"],
        )
    )
    assert len(insights) == 0

    # Test with languages array - should find insights with fr in the languages array
    insights = list(
        get_insights(
            server_type=ServerType.off,
            language_codes=["fr"],
        )
    )
    assert len(insights) == 2
    insight_ids = {insight.id for insight in insights}
    assert insight_ids == {insight_fr.id, insight_multi_lang.id}

    # Test with languages array - should find insights with es in the languages array
    insights = list(
        get_insights(
            server_type=ServerType.off,
            language_codes=["es"],
        )
    )
    assert len(insights) == 1
    assert insights[0].id == insight_multi_lang.id

    # Test without language_codes filter (should return all insights)
    insights = list(
        get_insights(
            server_type=ServerType.off,
        )
    )
    assert len(insights) == 5
    insight_ids = {insight.id for insight in insights}
    assert insight_ids == {
        insight_fr.id,
        insight_en.id,
        insight_de.id,
        insight_no_lang.id,
        insight_multi_lang.id,
    }
