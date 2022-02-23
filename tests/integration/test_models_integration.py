import pytest

from robotoff.models import AnnotationVote, ProductInsight

from .models_utils import AnnotationVoteFactory, ProductInsightFactory


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    AnnotationVote.delete().execute()
    ProductInsight.delete().execute()
    # Run the test case.
    yield
    # Tear down.
    AnnotationVote.delete().execute()
    ProductInsight.delete().execute()


def test_vote_cascade_on_insight_deletion(peewee_db):
    """Test AnnotationVote is cascading on insight deletion"""
    with peewee_db.atomic():
        insight = ProductInsightFactory(
            n_votes=2,
        )
        AnnotationVoteFactory(
            insight_id=insight,
        )
        AnnotationVoteFactory(
            insight_id=insight,
        )

    with peewee_db.atomic():
        insight.delete().execute()

    assert ProductInsight.select().count() == 0
    assert AnnotationVote.select().count() == 0
