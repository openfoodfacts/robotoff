import pytest

from robotoff import settings
from robotoff.models import AnnotationVote, ProductInsight

insight_id = "94371643-c2bc-4291-a585-af2cb1a5270a"


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
        insight = ProductInsight.create(
            id=insight_id,
            data="{}",
            barcode=1,
            type="category",
            n_votes=2,
            value_tag="en:seeds",
            server_domain=settings.OFF_SERVER_DOMAIN,
            automatic_processing=False,
            unique_scans_n=0,
            reserved_barcode=False,
        )
        AnnotationVote.create(
            insight_id=insight_id,
            value=1,
            device_id="device1",
        )
        AnnotationVote.create(
            insight_id=insight_id,
            value=1,
            device_id="device2",
        )

    with peewee_db.atomic():
        insight.delete().execute()

    assert ProductInsight.select().count() == 0
    assert AnnotationVote.select().count() == 0
