import base64
import uuid
from datetime import datetime

import pytest
from falcon import testing

from robotoff import settings
from robotoff.app import events
from robotoff.app.api import api
from robotoff.app.core import get_predictions
from robotoff.models import AnnotationVote, ProductInsight
from robotoff.off import OFFAuthentication

from .models_utils import (
    AnnotationVoteFactory,
    LogoAnnotationFactory,
    PredictionFactory,
    ProductInsightFactory,
    clean_db,
)

insight_id = "94371643-c2bc-4291-a585-af2cb1a5270a"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    clean_db()
    # Set up.
    ProductInsightFactory(id=insight_id, barcode=1)
    # Run the test case.
    yield
    clean_db()


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
                "value_tag": "en:seeds",
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
    AnnotationVoteFactory(
        insight_id=insight_id,
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
                "value_tag": "en:seeds",
                "question": "Does the product belong to this category?",
                "insight_id": insight_id,
                "insight_type": "category",
            }
        ],
        "status": "found",
    }


def test_popular_question_pagination(client, mocker):
    mocker.patch("robotoff.insights.question.get_product", return_value={})
    ProductInsight.delete().execute()  # remove default sample
    for i in range(0, 12):
        ProductInsightFactory(barcode=i, unique_scans_n=100 - i)

    result = client.simulate_get("/api/v1/questions/popular?count=5&page=1")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert [q["barcode"] for q in data["questions"]] == ["0", "1", "2", "3", "4"]
    result = client.simulate_get("/api/v1/questions/popular?count=5&page=2")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert [q["barcode"] for q in data["questions"]] == ["5", "6", "7", "8", "9"]
    result = client.simulate_get("/api/v1/questions/popular?count=5&page=3")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert [q["barcode"] for q in data["questions"]] == ["10", "11"]
    result = client.simulate_get("/api/v1/questions/popular?count=5&page=4")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "no_questions"
    assert len(data["questions"]) == 0


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
                "value_tag": "en:seeds",
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
    AnnotationVoteFactory(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter1",
    )
    AnnotationVoteFactory(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter2",
    )
    AnnotationVoteFactory(
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
    AnnotationVoteFactory(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter1",
    )
    AnnotationVoteFactory(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter2",
    )
    AnnotationVoteFactory(
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
def test_annotate_insight_majority_vote_overridden(client):
    # Add pre-existing insight votes.
    AnnotationVoteFactory(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter1",
    )
    AnnotationVoteFactory(
        insight_id=insight_id,
        value=1,
        device_id="yes-voter2",
    )
    AnnotationVoteFactory(
        insight_id=insight_id,
        value=-1,
        device_id="no-voter1",
    )
    AnnotationVoteFactory(
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


def test_annotate_insight_anonymous_then_authenticated(client, mocker):
    """Test that annotating first as anonymous, then, just after, as authenticated validate the anotation"""

    # mock because as we validate the insight, we will ask mongo for product
    mocker.patch(
        "robotoff.insights.annotate.get_product", return_value={"categories_tags": []}
    )
    add_category = mocker.patch("robotoff.insights.annotate.add_category")

    # first the user validates annotation without being connected
    result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "annotation": 1,
            "device_id": "voter1",
        },
    )

    assert result.status_code == 200
    assert result.json == {
        "description": "the annotation vote was saved",
        "status": "vote_saved",
    }

    # For non-authenticated users we expect the insight to not be validated, with only a vote being cast.
    votes = list(AnnotationVote.select())
    assert len(votes) == 1
    # no category added
    add_category.assert_not_called()

    insight = next(
        ProductInsight.select()
        .where(ProductInsight.id == insight_id)
        .dicts()
        .iterator()
    )

    assert not any(
        insight[key]
        for key in ("username", "completed_at", "annotation", "process_after")
    )
    assert insight.items() > {"n_votes": 1}.items()

    # then the user connects and vote for same insights

    auth = base64.b64encode(b"a:b").decode("ascii")
    authenticated_result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "annotation": 1,
            "device_id": "voter1",
        },
        headers={"Authorization": "Basic " + auth},
    )

    assert authenticated_result.status_code == 200
    assert authenticated_result.json == {
        "description": "the annotation was saved and sent to OFF",
        "status": "updated",
    }
    # We have the previous vote, but the last request should validate the insight directly
    votes = list(AnnotationVote.select())
    assert len(votes) == 1  # this is the previous vote

    insight = next(
        ProductInsight.select()
        .where(ProductInsight.id == insight_id)
        .dicts()
        .iterator()
    )
    # we still have the vote, but we also have an authenticated validation
    assert insight.items() > {"username": "a", "n_votes": 1, "annotation": 1}.items()
    assert insight.get("completed_at") is not None
    assert insight.get("completed_at") <= datetime.utcnow()
    # update was done
    add_category.assert_called_once_with(
        "1",  # barcode
        "en:seeds",  # category_tag
        insight_id=uuid.UUID(insight_id),
        server_domain=settings.OFF_SERVER_DOMAIN,
        auth=OFFAuthentication(username="a", password="b"),
    )


def test_annotation_event(client, monkeypatch, httpserver):
    """Test that annotation sends an event"""
    monkeypatch.setattr(settings, "EVENTS_API_URL", httpserver.url_for("/"))
    # setup a new event_processor, to be sure settings is taken into account
    monkeypatch.setattr(events, "event_processor", events.EventProcessor())
    # We expect to have a call to events server
    expected_event = {
        "event_type": "question_answered",
        "user_id": "a",
        "device_id": "test-device",
        "barcode": "1",
    }
    httpserver.expect_oneshot_request(
        "/", method="POST", json=expected_event
    ).respond_with_data("Done")
    with httpserver.wait(raise_assertions=True, stop_on_nohandler=True, timeout=2):
        result = client.simulate_post(
            "/api/v1/insights/annotate",
            params={
                "insight_id": insight_id,
                "annotation": -1,
                "device_id": "test-device",
            },
            headers={
                "Authorization": "Basic " + base64.b64encode(b"a:b").decode("ascii")
            },
        )
    assert result.status_code == 200


def test_prediction_collection_no_result(client):
    result = client.simulate_get("/api/v1/predictions/")
    assert result.status_code == 200
    assert result.json == {"count": 0, "predictions": [], "status": "no_predictions"}


def test_prediction_collection_no_filter(client):

    prediction1 = PredictionFactory(value_tag="en:seeds")
    result = client.simulate_get("/api/v1/predictions/")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["status"] == "found"
    prediction_data = data["predictions"]
    assert prediction_data[0]["id"] == prediction1.id
    assert prediction_data[0]["type"] == "category"
    assert prediction_data[0]["value_tag"] == "en:seeds"

    prediction2 = PredictionFactory(
        value_tag="en:beers", data={"sample": 1}, type="brand"
    )
    result = client.simulate_get("/api/v1/predictions/")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 2
    assert data["status"] == "found"
    prediction_data = sorted(data["predictions"], key=lambda d: d["id"])
    # we still have both predictions
    assert prediction_data[0]["id"] == prediction1.id
    # but also the second
    assert prediction_data[1]["id"] == prediction2.id
    assert prediction_data[1]["type"] == "brand"
    assert prediction_data[1]["value_tag"] == "en:beers"


def test_get_predictions():
    prediction1 = PredictionFactory(
        barcode="123", keep_types="category", value_tag="en:seeds"
    )
    prediction2 = PredictionFactory(
        barcode="123", keep_types="category", value_tag="en:beers"
    )
    prediction3 = PredictionFactory(
        barcode="123", keep_types="label", value_tag="en:eu-organic"
    )
    prediction4 = PredictionFactory(
        barcode="456", keep_types="label", value_tag="en:eu-organic"
    )

    actual_prediction1 = get_predictions(barcode="123")
    actual_items1 = [item.to_dict() for item in actual_prediction1]
    actual_items1.sort(key=lambda d: d["id"])
    assert len(actual_items1) == 3
    assert actual_items1[0]["id"] == prediction1.id
    assert actual_items1[0]["barcode"] == "123"
    assert actual_items1[0]["type"] == "category"
    assert actual_items1[0]["value_tag"] == "en:seeds"
    assert actual_items1[1]["value_tag"] == "en:beers"
    assert actual_items1[1]["id"] == prediction2.id
    assert actual_items1[2]["value_tag"] == "en:eu-organic"
    assert actual_items1[2]["id"] == prediction3.id

    # test that as we have no "brand" prediction, returned list is empty
    actual_prediction2 = get_predictions(keep_types=["brand"])
    assert list(actual_prediction2) == []

    # test that predictions are filtered based on "value_tag=en:eu-organic",
    # returns only "en:eu-organic" predictions
    actual_prediction3 = get_predictions(value_tag="en:eu-organic")
    actual_items3 = [item.to_dict() for item in actual_prediction3]
    actual_items3.sort(key=lambda d: d["id"])
    assert len(actual_items3) == 2
    assert actual_items3[0]["id"] == prediction3.id
    assert actual_items3[0]["barcode"] == "123"
    assert actual_items3[0]["type"] == "category"
    assert actual_items3[0]["value_tag"] == "en:eu-organic"
    assert actual_items3[1]["id"] == prediction4.id

    # test that we can filter "barcode", "value_tag", "keep_types" prediction
    actual_prediction4 = get_predictions(
        barcode="123", value_tag="en:eu-organic", keep_types=["category"]
    )
    actual_items4 = [item.to_dict() for item in actual_prediction4]
    assert actual_items4[0]["id"] == prediction3.id
    assert len(actual_items4) == 1

    # test to filter results with "label" and "category" prediction
    actual_prediction5 = get_predictions(keep_types=["label", "category"])
    actual_items5 = [item.to_dict() for item in actual_prediction5]
    assert len(actual_items5) == 4


def test_image_prediction_collection(client):
    result = client.simulate_get("/api/v1/images/prediction/collection/")
    assert result.status_code == 200

    logo_annotation_with_barcode = LogoAnnotationFactory(
        image_prediction__image__barcode="123"
    )
    logo_annotation_with_type = LogoAnnotationFactory(
        type="label", image_prediction__image__barcode="456"
    )

    # test with "barcode=123" and "with_logo=True"
    result = client.simulate_get(
        "/api/v1/images/prediction/collection",
        params={
            "barcode": "123",
            "with_logo": True,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["images"][0]["id"] == logo_annotation_with_barcode.id
    assert data["images"][0]["image_prediction"]["image"]["barcode"] == "123"

    # test with "type=label" and "with_logo=True"
    result = client.simulate_get(
        "/api/v1/images/prediction/collection",
        params={
            "type": "label",
            "with_logo": True,
        },
    )

    assert result.status_code == 200
    data = result.json
    data["images"].sort(key=lambda d: d["id"])
    assert data["count"] == 2
    assert data["images"][0]["id"] == logo_annotation_with_barcode.id
    assert data["images"][1]["id"] == logo_annotation_with_type.id

    # test with "barcode=456" and "with_logo=True"
    result = client.simulate_get(
        "/api/v1/images/prediction/collection",
        params={
            "barcode": "456",
            "with_logo": True,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["images"][0]["id"] == logo_annotation_with_type.id

    # test with "type=label" and "with_logo=False"
    result = client.simulate_get(
        "/api/v1/images/prediction/collection",
        params={
            "type": "label",
            "with_logo": False,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 0
