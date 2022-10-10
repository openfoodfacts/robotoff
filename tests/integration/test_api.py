import base64
import uuid
from datetime import datetime

import pytest
from falcon import testing

from robotoff import settings
from robotoff.app import events
from robotoff.app.api import api
from robotoff.models import AnnotationVote, LogoAnnotation, ProductInsight
from robotoff.off import OFFAuthentication

from .models_utils import (
    AnnotationVoteFactory,
    ImageModelFactory,
    ImagePredictionFactory,
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
    assert result.json == {
        "status_code": 1,
        "status": "saved",
        "description": "the annotation was saved",
    }

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

    # check if "annotated_result" is saved
    assert insight["annotated_result"] == 1


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
        "status_code": 9,
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
    assert result.json == {
        "status_code": 1,
        "status": "saved",
        "description": "the annotation was saved",
    }

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
    assert result.json == {
        "status_code": 1,
        "status": "saved",
        "description": "the annotation was saved",
    }

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
    assert result.json == {
        "status_code": 1,
        "status": "saved",
        "description": "the annotation was saved",
    }

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
        "status_code": 9,
        "status": "vote_saved",
        "description": "the annotation vote was saved",
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
        "status_code": 2,
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


def test_image_collection_no_result(client):
    result = client.simulate_get("/api/v1/images")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 0
    assert data["images"] == []
    assert data["status"] == "no_images"


def test_image_collection(client):
    image_model = ImageModelFactory(barcode="123")
    ImagePredictionFactory(image__barcode="456")

    result = client.simulate_get(
        "/api/v1/images",
        params={
            "count": "25",
            "page": "1",
            "barcode": "123",
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["images"][0]["id"] == image_model.id
    assert data["status"] == "found"

    result = client.simulate_get(
        "/api/v1/images",
        params={
            "barcode": "456",
            "with_predictions": True,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["images"][0]["barcode"] == "456"
    assert data["status"] == "found"

    result = client.simulate_get(
        "/api/v1/images",
        params={
            "count": "25",
            "page": "1",
            "with_predictions": False,
        },
    )

    assert result.status_code == 200
    assert data["count"] == 1
    assert data["images"][0]["barcode"] == "456"


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
    result = client.simulate_get("/api/v1/predictions")
    assert result.status_code == 200
    assert result.json == {"count": 0, "predictions": [], "status": "no_predictions"}


def test_prediction_collection_no_filter(client):

    prediction1 = PredictionFactory(value_tag="en:seeds")
    result = client.simulate_get("/api/v1/predictions")
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
    result = client.simulate_get("/api/v1/predictions")
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


def test_get_unanswered_questions_api_empty(client):
    ProductInsight.delete().execute()  # remove default sample
    result = client.simulate_get("/api/v1/questions/unanswered")

    assert result.status_code == 200
    assert result.json == {"count": 0, "questions": [], "status": "no_questions"}


def test_get_unanswered_questions_api(client):
    ProductInsight.delete().execute()  # remove default sample

    ProductInsightFactory(type="category", value_tag="en:apricot", barcode="123")

    ProductInsightFactory(type="label", value_tag="en:beer", barcode="456")

    ProductInsightFactory(type="nutrition", value_tag="en:soups", barcode="789")

    ProductInsightFactory(type="nutrition", value_tag="en:salad", barcode="302")

    ProductInsightFactory(type="nutrition", value_tag="en:salad", barcode="403")

    ProductInsightFactory(type="category", value_tag="en:soups", barcode="194")

    ProductInsightFactory(type="category", value_tag="en:soups", barcode="967")

    ProductInsightFactory(type="label", value_tag="en:beer", barcode="039")

    ProductInsightFactory(type="category", value_tag="en:apricot", barcode="492")

    ProductInsightFactory(type="category", value_tag="en:soups", barcode="594")

    ProductInsightFactory(
        type="category",
        value_tag="en:apricot",
        barcode="780",
        annotation=1,
    )

    ProductInsightFactory(
        type="category", value_tag="en:apricot", barcode="983", annotation=0
    )

    # test to get all "category" with "annotation=None"

    result = client.simulate_get(
        "/api/v1/questions/unanswered",
        params={
            "count": 5,
            "page": 1,
            "type": "category",
        },
    )
    assert result.status_code == 200
    data = result.json

    assert len(data) == 3
    assert data["questions"] == [["en:soups", 3], ["en:apricot", 2]]
    assert data["status"] == "found"

    # test to get all "label" with "annotation=None"

    result = client.simulate_get(
        "/api/v1/questions/unanswered", params={"type": "label"}
    )
    assert result.status_code == 200
    data = result.json
    assert len(data) == 3
    assert len(data["questions"]) == 1
    assert data["questions"] == [["en:beer", 2]]

    # test to get all "nutrition" with "annotation=None"

    result = client.simulate_get(
        "/api/v1/questions/unanswered", params={"type": "nutrition"}
    )
    assert result.status_code == 200
    data = result.json
    assert len(data) == 3
    assert len(data["questions"]) == 2
    assert data["questions"] == [["en:salad", 2], ["en:soups", 1]]
    assert data["status"] == "found"


def test_get_unanswered_questions_api_with_country_filter(client):
    ProductInsight.delete().execute()  # remove default sample

    # test for filter with "country"

    ProductInsightFactory(
        type="location", value_tag="en:dates", barcode="032", countries=["en:india"]
    )
    ProductInsightFactory(
        type="location", value_tag="en:dates", barcode="033", countries=["en:france"]
    )

    result = client.simulate_get(
        "/api/v1/questions/unanswered", params={"country": "en:india"}
    )
    assert result.status_code == 200
    data = result.json
    assert len(data) == 3
    assert len(data["questions"]) == 1
    assert data["questions"] == [["en:dates", 1]]
    assert data["status"] == "found"


def test_get_unanswered_questions_pagination(client):
    ProductInsight.delete().execute()  # remove default sample
    for i in range(0, 12):
        ProductInsightFactory(type="nutrition", value_tag=f"en:soups-{i:02}")

    result = client.simulate_get(
        "/api/v1/questions/unanswered?count=5&page=1&type=nutrition"
    )
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert len(data["questions"]) == 5
    questions = data["questions"]

    result = client.simulate_get(
        "/api/v1/questions/unanswered?count=5&page=2&type=nutrition"
    )
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert len(data["questions"]) == 5
    questions.extend(data["questions"])

    result = client.simulate_get(
        "/api/v1/questions/unanswered?count=5&page=3&type=nutrition"
    )
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert len(data["questions"]) == 2
    questions.extend(data["questions"])

    questions.sort()
    assert questions == [
        ["en:soups-00", 1],
        ["en:soups-01", 1],
        ["en:soups-02", 1],
        ["en:soups-03", 1],
        ["en:soups-04", 1],
        ["en:soups-05", 1],
        ["en:soups-06", 1],
        ["en:soups-07", 1],
        ["en:soups-08", 1],
        ["en:soups-09", 1],
        ["en:soups-10", 1],
        ["en:soups-11", 1],
    ]


def test_image_prediction_collection_empty(client):
    result = client.simulate_get("/api/v1/images/prediction/collection/")
    assert result.status_code == 200


def test_image_prediction_collection(client):

    logo_annotation_category_123 = LogoAnnotationFactory(
        image_prediction__image__barcode="123",
        image_prediction__type="category",
    )
    prediction_category_123 = logo_annotation_category_123.image_prediction
    logo_annotation_label_789 = LogoAnnotationFactory(
        image_prediction__image__barcode="789",
        image_prediction__type="label",
    )
    prediction_label_789 = logo_annotation_label_789.image_prediction

    prediction_label_789_no_logo = ImagePredictionFactory(
        image__barcode="789", type="label"
    )

    # test with "barcode=123" and "with_logo=True"
    result = client.simulate_get(
        "/api/v1/images/prediction/collection",
        params={
            "barcode": "123",
            "with_logo": 1,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["image_predictions"][0]["id"] == prediction_category_123.id
    assert data["image_predictions"][0]["image"]["barcode"] == "123"

    # test with "type=label" and "with_logo=True"
    result = client.simulate_get(
        "/api/v1/images/prediction/collection",
        params={
            "type": "label",
            "with_logo": 1,
        },
    )

    assert result.status_code == 200
    data = result.json
    data["image_predictions"].sort(key=lambda d: d["id"])
    assert data["count"] == 2
    assert data["image_predictions"][0]["id"] == prediction_label_789.id
    assert data["image_predictions"][1]["id"] == prediction_label_789_no_logo.id

    # test with "barcode=456" and "with_logo=True"
    result = client.simulate_get(
        "/api/v1/images/prediction/collection",
        params={
            "barcode": "456",
            "with_logo": 1,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 0
    assert data["image_predictions"] == []

    # test with "type=label" and "with_logo=False"
    result = client.simulate_get(
        "/api/v1/images/prediction/collection",
        params={
            "type": "label",
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["image_predictions"][0]["id"] == prediction_label_789_no_logo.id


def test_logo_annotation_collection_empty(client):
    result = client.simulate_get("/api/v1/annotation/collection/")
    assert result.status_code == 200
    assert result.json == {"count": 0, "annotation": [], "status": "no_annotation"}


def test_logo_annotation_collection_api(client):
    LogoAnnotation.delete().execute()  # remove default sample

    annotation_123_1 = LogoAnnotationFactory(
        image_prediction__image__barcode="123",
        annotation_value_tag="etorki",
        annotation_type="brand",
    )

    annotation_123_2 = LogoAnnotationFactory(
        image_prediction__image__barcode="123",
        annotation_value_tag="etorki",
        annotation_type="brand",
    )

    annotation_295 = LogoAnnotationFactory(
        image_prediction__image__barcode="295",
        annotation_value_tag="cheese",
        annotation_type="dairies",
    )

    annotation_789 = LogoAnnotationFactory(
        image_prediction__image__barcode="789",
        annotation_value_tag="creme",
        annotation_type="dairies",
    )

    annotation_306 = LogoAnnotationFactory(
        image_prediction__image__barcode="306",
        annotation_value_tag="yoghurt",
        annotation_type="dairies",
    )

    annotation_604 = LogoAnnotationFactory(
        image_prediction__image__barcode="604",
        annotation_value_tag="meat",
        annotation_type="category",
    )

    # test with "barcode"

    result = client.simulate_get(
        "/api/v1/annotation/collection",
        params={
            "barcode": "123",
        },
    )
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 2
    annotation_data = sorted(data["annotation"], key=lambda d: d["id"])
    assert annotation_data[0]["id"] == annotation_123_1.id
    assert annotation_data[1]["id"] == annotation_123_2.id
    assert annotation_data[0]["image_prediction"]["image"]["barcode"] == "123"
    assert annotation_data[1]["image_prediction"]["image"]["barcode"] == "123"
    assert annotation_data[0]["annotation_type"] == "brand"
    assert annotation_data[1]["annotation_type"] == "brand"
    assert annotation_data[0]["annotation_value_tag"] == "etorki"
    assert annotation_data[1]["annotation_value_tag"] == "etorki"

    # test with "value_tag"

    result = client.simulate_get(
        "/api/v1/annotation/collection",
        params={"value_tag": "cheese"},
    )
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["annotation"][0]["id"] == annotation_295.id
    assert data["annotation"][0]["image_prediction"]["image"]["barcode"] == "295"
    assert data["annotation"][0]["annotation_type"] == "dairies"
    assert data["annotation"][0]["annotation_value_tag"] == "cheese"

    # test with "types"

    result = client.simulate_get(
        "/api/v1/annotation/collection",
        params={
            "types": ["category", "dairies"],
        },
    )
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 4
    annotations = sorted(data["annotation"], key=lambda a: a["id"])
    assert annotations[0]["id"] == annotation_295.id
    assert annotations[0]["image_prediction"]["image"]["barcode"] == "295"
    assert annotations[1]["id"] == annotation_789.id
    assert annotations[1]["image_prediction"]["image"]["barcode"] == "789"
    assert annotations[2]["id"] == annotation_306.id
    assert annotations[2]["image_prediction"]["image"]["barcode"] == "306"
    assert annotations[3]["id"] == annotation_604.id
    assert annotations[3]["image_prediction"]["image"]["barcode"] == "604"


def test_logo_annotation_collection_pagination(client):
    LogoAnnotation.delete().execute()  # remove default sample
    for i in range(0, 12):
        LogoAnnotationFactory(
            annotation_type="label", annotation_value_tag=f"no lactose-{i:02}"
        )

    for i in range(0, 2):
        LogoAnnotationFactory(
            annotation_type="vegan", annotation_value_tag=f"truffle cake-{i:02}"
        )

    for i in range(0, 2):
        LogoAnnotationFactory(
            annotation_type="category", annotation_value_tag=f"sea food-{i:02}"
        )

    result = client.simulate_get(
        "/api/v1/annotation/collection?count=5&page=1&types=label"
    )

    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert len(data["annotation"]) == 5
    annotation_data = [q["annotation_value_tag"] for q in data["annotation"]]
    annotations = annotation_data

    result = client.simulate_get(
        "/api/v1/annotation/collection?count=5&page=2&types=label"
    )

    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert len(data["annotation"]) == 5
    annotation_data = [q["annotation_value_tag"] for q in data["annotation"]]
    annotations.extend(annotation_data)

    result = client.simulate_get(
        "/api/v1/annotation/collection?count=5&page=3&types=label"
    )

    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert len(data["annotation"]) == 2
    annotation_data = [q["annotation_value_tag"] for q in data["annotation"]]
    annotations.extend(annotation_data)

    # test for multiple values in "types"

    result = client.simulate_get(
        "/api/v1/annotation/collection?count=5&page=1&types=category&types=vegan"
    )

    data = result.json
    assert data["count"] == 4
    assert data["status"] == "found"
    assert len(data["annotation"]) == 4
    annotation_data = [q["annotation_value_tag"] for q in data["annotation"]]
    annotations.extend(annotation_data)

    annotations.sort()
    assert annotations == [
        "no lactose-00",
        "no lactose-01",
        "no lactose-02",
        "no lactose-03",
        "no lactose-04",
        "no lactose-05",
        "no lactose-06",
        "no lactose-07",
        "no lactose-08",
        "no lactose-09",
        "no lactose-10",
        "no lactose-11",
        "sea food-00",
        "sea food-01",
        "truffle cake-00",
        "truffle cake-01",
    ]
