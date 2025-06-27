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


def test_filter_by_lc():
    """Test that insights can be filtered by language_codes."""
    # Create insights with different language codes
    insight_fr = ProductInsightFactory(
        server_type=ServerType.off.name,
        lc=["fr"],
    )
    insight_en = ProductInsightFactory(
        server_type=ServerType.off.name,
        lc=["en"],
    )
    insight_de = ProductInsightFactory(
        server_type=ServerType.off.name,
        lc=["de"],
    )
    insight_no_lang = ProductInsightFactory(
        # No language code
        server_type=ServerType.off.name,
    )

    # Test filtering by a single language code
    insights = list(
        get_insights(
            server_type=ServerType.off,
            lc=["fr"],
        )
    )
    assert len(insights) == 1
    assert insights[0].id == insight_fr.id

    # Test filtering by multiple language codes
    insights = list(
        get_insights(
            server_type=ServerType.off,
            lc=["fr", "en"],
        )
    )
    assert len(insights) == 2
    insight_ids = {insight.id for insight in insights}
    assert insight_ids == {insight_fr.id, insight_en.id}

    # Test filtering by a language code that doesn't exist
    insights = list(
        get_insights(
            server_type=ServerType.off,
            lc=["es"],
        )
    )
    assert len(insights) == 0

    # Test without language_codes filter (should return all insights)
    insights = list(
        get_insights(
            server_type=ServerType.off,
        )
    )
    assert len(insights) == 4
    insight_ids = {insight.id for insight in insights}
    assert insight_ids == {
        insight_fr.id,
        insight_en.id,
        insight_de.id,
        insight_no_lang.id,
    }
