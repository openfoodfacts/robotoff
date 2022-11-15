from datetime import datetime, timedelta

import pytest

from robotoff import scheduler
from robotoff.models import ProductInsight

from .models_utils import ProductInsightFactory, clean_db


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    clean_db()
    # Run the test case.
    yield
    clean_db()


def test_mark_insights():
    now = datetime.utcnow()
    # not automatic
    not_auto = ProductInsightFactory(automatic_processing=False)
    # already marked
    marked = ProductInsightFactory(
        automatic_processing=True,
        annotation=None,
        process_after=now - timedelta(minutes=2),
    )
    # already annotated
    annotated = ProductInsightFactory(automatic_processing=True, annotation=1)
    # ready to be marked
    ready1 = ProductInsightFactory(automatic_processing=True)
    ready2 = ProductInsightFactory(automatic_processing=True)
    # run
    start = datetime.utcnow()
    num_marked = scheduler.mark_insights()
    end = datetime.utcnow()
    ten_min = timedelta(minutes=10)
    # two marked
    assert num_marked == 2
    assert (
        start + ten_min < ProductInsight.get(id=ready1.id).process_after < end + ten_min
    )
    assert (
        start + ten_min < ProductInsight.get(id=ready2.id).process_after < end + ten_min
    )
    # other did not change
    assert ProductInsight.get(id=not_auto).process_after is None
    assert ProductInsight.get(id=annotated).process_after is None
    assert ProductInsight.get(id=marked).process_after < start

    # run again should not mark anything more
    num_marked = scheduler.mark_insights()
    assert num_marked == 0
