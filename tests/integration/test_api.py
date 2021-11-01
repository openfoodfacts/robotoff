import base64

import pytest
from falcon import testing

from robotoff.app.api import api
from robotoff.models import AnnotationVote, ProductInsight

insight_id = "94371643-c2bc-4291-a585-af2cb1a5270a"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down():
    # Set up.
    ProductInsight.create(
        id=insight_id,
        data="{}",
        barcode=1,
        type="category",
        n_votes=0,
        latent=False,
        value_tag="en:seeds",
        server_domain="api.openfoodfacts.net",
        automatic_processing=False,
        unique_scans_n=0,
        reserved_barcode=False,
    )

    # Run the test case.
    yield

    # Tear down.
    AnnotationVote.delete().execute()
    ProductInsight.delete().execute()


def client():
    return testing.TestClient(api)


def test_random_question():
    cl = client()
    result = cl.simulate_get("/api/v1/questions/random")

    assert result.status_code == 200
    assert result.json == {
        "count": 1,
        "questions": [
            {
                "barcode": "1",
                "type": "add-binary",
                "value": "Seeds",
                "question": "Does the product belong to this category?",
                "insight_id": insight_id,
                "insight_type": "category",
            }
        ],
        "status": "found",
    }


def test_popular_question():
    cl = client()
    result = cl.simulate_get("/api/v1/questions/popular")

    assert result.status_code == 200
    assert result.json == {
        "count": 1,
        "questions": [
            {
                "barcode": "1",
                "type": "add-binary",
                "value": "Seeds",
                "question": "Does the product belong to this category?",
                "insight_id": insight_id,
                "insight_type": "category",
            }
        ],
        "status": "found",
    }


def test_barcode_question():
    cl = client()
    result = cl.simulate_get("/api/v1/questions/2")

    assert result.status_code == 200
    assert result.json == {"questions": [], "status": "no_questions"}

    result = cl.simulate_get("/api/v1/questions/1")

    assert result.status_code == 200
    assert result.json == {
        "questions": [
            {
                "barcode": "1",
                "type": "add-binary",
                "value": "Seeds",
                "question": "Does the product belong to this category?",
                "insight_id": insight_id,
                "insight_type": "category",
            }
        ],
        "status": "found",
    }


def test_annotate_insight_authenticated():
    cl = client()
    result = cl.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "annotation": -1,
        },
        headers={"Authorization": "Basic " + base64.b64encode(b"a:b").decode("ascii")},
    )

    assert result.status_code == 200
    assert result.json == {"description": "the annotation was saved", "status": "saved"}

    # For authenticated users we expect the insight to be validated directly, tracking the username of the annotator.
    votes = list(AnnotationVote.select())
    assert len(votes) == 0

    insight = next(
        ProductInsight.select()
        .where(ProductInsight.id == insight_id)
        .dicts()
        .iterator()
    )
    assert insight.items() > {"username": "a", "annotation": -1, "n_votes": 0}.items()
    assert "completed_at" in insight


def test_annotate_insight_not_enough_votes():
    cl = client()
    result = cl.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "annotation": -1,
            "device_id": "voter1",
        },
    )

    assert result.status_code == 200
    assert result.json == {
        "description": "the annotation vote was saved",
        "status": "vote_saved",
    }

    # For non-authenticated users we expect the insight to not be validated, with only a vote being cast.
    votes = list(AnnotationVote.select().dicts())
    assert len(votes) == 1

    assert votes[0]["value"] == -1
    assert votes[0]["username"] is None
    assert votes[0]["device_id"] == "voter1"

    insight = next(
        ProductInsight.select()
        .where(ProductInsight.id == insight_id)
        .dicts()
        .iterator()
    )

    assert all(
        [
            val is None
            for key, val in insight.items()
            if key in {"username", "completed_at", "annotation"}
        ]
    )
    assert insight.items() > {"n_votes": 1}.items()


def test_annotate_insight_majority_annotation():
    # Add pre-existing insight votes.
    AnnotationVote.create(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter1",
    )
    AnnotationVote.create(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter2",
    )
    AnnotationVote.create(
        insight_id=insight_id,
        value=-1,
        device_id="no-voter1",
    )

    cl = client()
    result = cl.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "device_id": "yes-voter3",
            "annotation": 1,
            "update": False,  # disable actually updating the product in PO.
        },
    )

    assert result.status_code == 200
    assert result.json == {"description": "the annotation was saved", "status": "saved"}

    votes = list(AnnotationVote.select())
    assert len(votes) == 4

    insight = next(
        ProductInsight.select()
        .where(ProductInsight.id == insight_id)
        .dicts()
        .iterator()
    )
    # The insight should be annoted with '1', with a None username since this was resolved with an
    # anonymous vote.
    assert insight.items() > {"annotation": 1, "username": None, "n_votes": 4}.items()


# This test checks for handling of cases where we have 2 votes for 2 different annotations.
def test_annotate_insight_opposite_votes():
    # Add pre-existing insight votes.
    AnnotationVote.create(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter1",
    )
    AnnotationVote.create(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter2",
    )
    AnnotationVote.create(
        insight_id=insight_id,
        value=-1,
        device_id="no-voter1",
    )

    cl = client()
    result = cl.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "device_id": "no-voter2",
            "annotation": -1,
            "update": False,  # disable actually updating the product in PO.
        },
    )

    assert result.status_code == 200
    assert result.json == {"description": "the annotation was saved", "status": "saved"}

    votes = list(AnnotationVote.select())
    assert len(votes) == 4

    insight = next(
        ProductInsight.select()
        .where(ProductInsight.id == insight_id)
        .dicts()
        .iterator()
    )
    # The insight should be annoted with '0', with a None username since this was resolved with an
    # anonymous vote.
    assert insight.items() > {"annotation": 0, "username": None, "n_votes": 4}.items()


# This test checks for handling of cases where we have 3 votes for one annotation,
# but the follow-up has 2 votes.
def test_annotate_insight_majority_vote_overriden():
    # Add pre-existing insight votes.
    AnnotationVote.create(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter1",
    )
    AnnotationVote.create(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter2",
    )
    AnnotationVote.create(
        insight_id=insight_id,
        value=-1,
        device_id="no-voter1",
    )
    AnnotationVote.create(
        insight_id=insight_id,
        value=-1,
        device_id="no-voter2",
    )

    cl = client()
    result = cl.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "device_id": "no-voter3",
            "annotation": -1,
            "update": False,  # disable actually updating the product in PO.
        },
    )

    assert result.status_code == 200
    assert result.json == {"description": "the annotation was saved", "status": "saved"}

    votes = list(AnnotationVote.select())
    assert len(votes) == 5

    insight = next(
        ProductInsight.select()
        .where(ProductInsight.id == insight_id)
        .dicts()
        .iterator()
    )
    # The insight should be annoted with '0', with a None username since this was resolved with an
    # anonymous vote.
    assert insight.items() > {"annotation": 0, "username": None, "n_votes": 5}.items()
