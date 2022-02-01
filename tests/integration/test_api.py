import base64

import pytest
from falcon import testing

from robotoff import settings
from robotoff.app.api import api
from robotoff.models import AnnotationVote, ProductInsight

insight_id = "94371643-c2bc-4291-a585-af2cb1a5270a"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    AnnotationVote.delete().execute()
    ProductInsight.delete().execute()
    # Set up.
    ProductInsight.create(
        id=insight_id,
        data="{}",
        barcode=1,
        type="category",
        n_votes=0,
        value_tag="en:seeds",
        server_domain=settings.OFF_SERVER_DOMAIN,
        automatic_processing=False,
        unique_scans_n=0,
        reserved_barcode=False,
    )

    # Run the test case.
    yield

    # Tear down.
    AnnotationVote.delete().execute()
    ProductInsight.delete().execute()


@pytest.fixture()
def client():
    return testing.TestClient(api)


def test_random_question(client, mocker):
    product = {"selected_images": {"ingredients": {"display": {"fr": "foo"}}}}
    mocker.patch("robotoff.insights.question.get_product", return_value=product)
    result = client.simulate_get("/api/v1/questions/random")

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
                "source_image_url": "foo",
            }
        ],
        "status": "found",
    }


def test_random_question_user_has_already_seen(client, mocker):
    mocker.patch("robotoff.insights.question.get_product", return_value={})
    AnnotationVote.create(
        insight_id=insight_id,
        value=1,
        device_id="device1",
    )

    result = client.simulate_get("/api/v1/questions/random?device_id=device1")

    assert result.status_code == 200
    assert result.json == {"count": 0, "questions": [], "status": "no_questions"}


def test_popular_question(client, mocker):
    mocker.patch("robotoff.insights.question.get_product", return_value={})
    result = client.simulate_get("/api/v1/questions/popular")

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


def test_barcode_question_not_found(client):
    result = client.simulate_get("/api/v1/questions/2")

    assert result.status_code == 200
    assert result.json == {"questions": [], "status": "no_questions"}


def test_barcode_question(client, mocker):
    mocker.patch("robotoff.insights.question.get_product", return_value={})
    result = client.simulate_get("/api/v1/questions/1")

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


def test_annotate_insight_authenticated(client):
    result = client.simulate_post(
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


def test_annotate_insight_not_enough_votes(client):
    result = client.simulate_post(
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

    assert not any(insight[key] for key in ("username", "completed_at", "annotation"))
    assert insight.items() > {"n_votes": 1}.items()


def test_annotate_insight_majority_annotation(client):
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

    result = client.simulate_post(
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
def test_annotate_insight_opposite_votes(client):
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

    result = client.simulate_post(
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
def test_annotate_insight_majority_vote_overriden(client):
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

    result = client.simulate_post(
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
