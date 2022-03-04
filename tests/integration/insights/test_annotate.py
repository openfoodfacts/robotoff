import pytest

from robotoff.insights.annotate import CategoryAnnotator
from robotoff.models import ProductInsight

from ..models_utils import ProductInsightFactory


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    ProductInsight.delete().execute()
    # Run the test case.
    yield
    # Tear down.
    ProductInsight.delete().execute()


def test_annotation_fails_is_rolledback(mocker):
    annotator = CategoryAnnotator  # should be enough to test with one annotator

    # make it raise
    mocked = mocker.patch.object(
        annotator, "process_annotation", side_effect=Exception("Blah")
    )
    insight = ProductInsightFactory()
    with pytest.raises(Exception):
        annotator().annotate(
            insight=insight,
            annotation=1,
            automatic=True,
        )
    insight = ProductInsight.get(id=insight.id)
    # unchanged
    assert insight.completed_at is None
    assert insight.annotation is None
    # while process_annotation was called
    assert mocked.called
