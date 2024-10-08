import base64
import datetime
import uuid

import pytest
import requests
from falcon import testing

from robotoff.app import events
from robotoff.app.api import api
from robotoff.models import AnnotationVote, LogoAnnotation, ProductInsight
from robotoff.off import OFFAuthentication
from robotoff.prediction.langid import LanguagePrediction
from robotoff.types import PredictionType, ProductIdentifier, ServerType

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
DEFAULT_BARCODE = "00000001"
DEFAULT_SERVER_TYPE = ServerType.off
DEFAULT_PRODUCT_ID = ProductIdentifier(DEFAULT_BARCODE, DEFAULT_SERVER_TYPE)


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        # clean db
        clean_db()
        # Set up.
        ProductInsightFactory(id=insight_id, barcode=DEFAULT_BARCODE)
    # Run the test case.
    yield
    with peewee_db:
        clean_db()


@pytest.fixture()
def client():
    return testing.TestClient(api)


def test_random_question(client, mocker):
    product = {
        "images": {
            "ingredients_fr": {
                "rev": "51",
                "sizes": {
                    "100": {"h": 75, "w": 100},
                    "400": {"h": 300, "w": 400},
                    "full": {"h": 1500, "w": 2000},
                },
            }
        }
    }
    mocker.patch("robotoff.insights.question.get_product", return_value=product)
    result = client.simulate_get("/api/v1/questions?order_by=random")

    assert result.status_code == 200
    assert result.json == {
        "count": 1,
        "questions": [
            {
                "barcode": "00000001",
                "type": "add-binary",
                "value": "Seeds",
                "value_tag": "en:seeds",
                "question": "Does the product belong to this category?",
                "insight_id": insight_id,
                "insight_type": "category",
                "server_type": "off",
                "source_image_url": "https://images.openfoodfacts.net/images/products/000/000/000/0001/ingredients_fr.51.400.jpg",
            }
        ],
        "status": "found",
    }


def test_random_question_user_has_already_seen(client, mocker, peewee_db):
    mocker.patch("robotoff.insights.question.get_product", return_value={})
    with peewee_db:
        AnnotationVoteFactory(
            insight_id=insight_id,
            device_id="device1",
        )

    result = client.simulate_get("/api/v1/questions?order_by=random&device_id=device1")

    assert result.status_code == 200
    assert result.json == {"count": 0, "questions": [], "status": "no_questions"}


def test_popular_question(client, mocker):
    mocker.patch("robotoff.insights.question.get_product", return_value={})
    result = client.simulate_get("/api/v1/questions?order_by=popularity")

    assert result.status_code == 200
    assert result.json == {
        "count": 1,
        "questions": [
            {
                "barcode": "00000001",
                "type": "add-binary",
                "value": "Seeds",
                "value_tag": "en:seeds",
                "question": "Does the product belong to this category?",
                "insight_id": insight_id,
                "insight_type": "category",
                "server_type": "off",
            }
        ],
        "status": "found",
    }


def test_popular_question_pagination(client, mocker, peewee_db):
    mocker.patch("robotoff.insights.question.get_product", return_value={})

    with peewee_db:
        ProductInsight.delete().execute()  # remove default sample
        for i in range(0, 12):
            ProductInsightFactory(barcode=i, unique_scans_n=100 - i)

    result = client.simulate_get("/api/v1/questions?order_by=popularity&count=5&page=1")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert [q["barcode"] for q in data["questions"]] == ["0", "1", "2", "3", "4"]
    result = client.simulate_get("/api/v1/questions?order_by=popularity&count=5&page=2")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert [q["barcode"] for q in data["questions"]] == ["5", "6", "7", "8", "9"]
    result = client.simulate_get("/api/v1/questions?order_by=popularity&count=5&page=3")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "found"
    assert [q["barcode"] for q in data["questions"]] == ["10", "11"]
    result = client.simulate_get("/api/v1/questions?order_by=popularity&count=5&page=4")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 12
    assert data["status"] == "no_questions"
    assert len(data["questions"]) == 0


def test_question_rank_by_confidence(client, mocker, peewee_db):
    mocker.patch("robotoff.insights.question.get_source_image_url", return_value=None)

    with peewee_db:
        ProductInsight.delete().execute()  # remove default sample
        ProductInsightFactory(
            barcode="1", type="category", value_tag="en:salmon", confidence=0.9
        )
        ProductInsightFactory(
            barcode="3", type="category", value_tag="en:breads", confidence=0.4
        )
        ProductInsightFactory(
            barcode="2", type="label", value_tag="en:eu-organic", confidence=0.7
        )
        ProductInsightFactory(
            barcode="4", type="brand", value_tag="carrefour", confidence=None
        )

    result = client.simulate_get("/api/v1/questions?order_by=confidence")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 4
    assert data["status"] == "found"
    assert [q["barcode"] for q in data["questions"]] == ["1", "2", "3", "4"]


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
                "barcode": "00000001",
                "type": "add-binary",
                "value": "Seeds",
                "value_tag": "en:seeds",
                "question": "Does the product belong to this category?",
                "insight_id": insight_id,
                "insight_type": "category",
                "server_type": "off",
            }
        ],
        "status": "found",
    }


def test_annotate_insight_authenticated(client, peewee_db):
    result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "annotation": 0,
        },
        headers={"Authorization": "Basic " + base64.b64encode(b"a:b").decode("ascii")},
    )

    assert result.status_code == 200
    assert result.json == {
        "status_code": 1,
        "status": "saved",
        "description": "the annotation was saved",
    }

    # For authenticated users we expect the insight to be validated directly,
    # tracking the username of the annotator.
    with peewee_db:
        votes = list(AnnotationVote.select())
        assert len(votes) == 0

        insight = next(
            ProductInsight.select()
            .where(ProductInsight.id == insight_id)
            .dicts()
            .iterator()
        )
        assert (
            insight.items() > {"username": "a", "annotation": 0, "n_votes": 0}.items()
        )
        assert "completed_at" in insight

    # check if "annotated_result" is saved
    assert insight["annotated_result"] == 1


def test_annotate_insight_authenticated_ignore(client, peewee_db):
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
        "status_code": 9,
        "status": "vote_saved",
        "description": "the annotation vote was saved",
    }

    with peewee_db:
        votes = list(AnnotationVote.select())
        assert len(votes) == 1

        insight = next(
            ProductInsight.select()
            .where(ProductInsight.id == insight_id)
            .dicts()
            .iterator()
        )
        assert (
            insight.items()
            > {"username": None, "annotation": None, "n_votes": 0}.items()
        )


def test_annotate_insight_not_enough_votes(client, peewee_db):
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
        "status_code": 9,
    }

    # For non-authenticated users we expect the insight to not be validated,
    # with only a vote being cast.
    with peewee_db:
        votes = list(AnnotationVote.select().dicts())
    assert len(votes) == 1

    assert votes[0]["value"] == 1
    assert votes[0]["username"] is None
    assert votes[0]["device_id"] == "voter1"
    with peewee_db:
        insight = next(
            ProductInsight.select()
            .where(ProductInsight.id == insight_id)
            .dicts()
            .iterator()
        )

    assert not any(insight[key] for key in ("username", "completed_at", "annotation"))
    assert insight.items() > {"n_votes": 1}.items()


def test_annotate_insight_majority_annotation(client, peewee_db):
    # Add pre-existing insight votes.
    with peewee_db:
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
            value=0,
            device_id="no-voter1",
        )
        AnnotationVoteFactory(
            insight_id=insight_id,
            value=-1,
            device_id="ignore-voter1",
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

    with peewee_db:
        votes = list(AnnotationVote.select())
        assert len(votes) == 5

        insight = next(
            ProductInsight.select()
            .where(ProductInsight.id == insight_id)
            .dicts()
            .iterator()
        )
    # The insight should be annoted with '1', with a None username since this
    # was resolved with an anonymous vote. `n_votes = 4, as -1 votes are not
    # considered
    assert insight.items() > {"annotation": 1, "username": None, "n_votes": 4}.items()


# This test checks for handling of cases where we have 2 votes for 2 different
# annotations.
def test_annotate_insight_opposite_votes(client, peewee_db):
    # Add pre-existing insight votes.
    with peewee_db:
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
            value=0,
            device_id="no-voter1",
        )

    result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "device_id": "no-voter2",
            "annotation": 0,
            "update": False,  # disable actually updating the product in PO.
        },
    )

    assert result.status_code == 200
    assert result.json == {
        "status_code": 1,
        "status": "saved",
        "description": "the annotation was saved",
    }

    with peewee_db:
        votes = list(AnnotationVote.select())
        assert len(votes) == 4

        insight = next(
            ProductInsight.select()
            .where(ProductInsight.id == insight_id)
            .dicts()
            .iterator()
        )
    # The insight should be annoted with '-1', with a None username since this
    # was resolved with an anonymous vote.
    assert insight.items() > {"annotation": -1, "username": None, "n_votes": 4}.items()


# This test checks for handling of cases where we have 3 votes for one
# annotation, but the follow-up has 2 votes.
def test_annotate_insight_majority_vote_overridden(client, peewee_db):
    # Add pre-existing insight votes.
    with peewee_db:
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
            value=0,
            device_id="no-voter1",
        )
        AnnotationVoteFactory(
            insight_id=insight_id,
            value=0,
            device_id="no-voter2",
        )

    result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": insight_id,
            "device_id": "no-voter3",
            "annotation": 0,
            "update": False,  # disable actually updating the product in PO.
        },
    )

    assert result.status_code == 200
    assert result.json == {
        "status_code": 1,
        "status": "saved",
        "description": "the annotation was saved",
    }

    with peewee_db:
        votes = list(AnnotationVote.select())
        assert len(votes) == 5

        insight = next(
            ProductInsight.select()
            .where(ProductInsight.id == insight_id)
            .dicts()
            .iterator()
        )
    # The insight should be annoted with '0', with a None username since this
    # was resolved with an anonymous vote.
    assert insight.items() > {"annotation": -1, "username": None, "n_votes": 5}.items()


def test_annotate_insight_anonymous_then_authenticated(client, mocker, peewee_db):
    """Test that annotating first as anonymous, then, just after, as
    authenticated validate the anotation"""

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

    # For non-authenticated users we expect the insight to not be validated,
    # with only a vote being cast.
    with peewee_db:
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
    # We have the previous vote, but the last request should validate the
    # insight directly
    with peewee_db:
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
    assert insight.get("completed_at") <= datetime.datetime.now()
    # update was done
    add_category.assert_called_once_with(
        DEFAULT_PRODUCT_ID,
        "en:seeds",  # category_tag
        insight_id=uuid.UUID(insight_id),
        auth=OFFAuthentication(username="a", password="b"),
        is_vote=False,
    )


def test_image_collection_no_result(client):
    result = client.simulate_get("/api/v1/images")
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 0
    assert data["images"] == []
    assert data["status"] == "no_images"


def test_image_collection(client, peewee_db):
    with peewee_db:
        image_model = ImageModelFactory(barcode="00000123")
        ImagePredictionFactory(image__barcode="00000456")

    result = client.simulate_get(
        "/api/v1/images",
        params={
            "count": "25",
            "page": "1",
            "barcode": "00000123",
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
            "barcode": "00000456",
            "with_predictions": True,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["images"][0]["barcode"] == "00000456"
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
    assert data["images"][0]["barcode"] == "00000456"


def test_annotation_event(client, monkeypatch, httpserver):
    """Test that annotation sends an event"""
    monkeypatch.setenv("EVENTS_API_URL", httpserver.url_for("/"))
    # setup a new event_processor, to be sure settings is taken into account
    monkeypatch.setattr(events, "event_processor", events.EventProcessor())
    # We expect to have a call to events server
    expected_event = {
        "event_type": "question_answered",
        "user_id": "a",
        "device_id": "test-device",
        "barcode": "00000001",
        "server_type": "off",
    }
    httpserver.expect_oneshot_request(
        "/", method="POST", json=expected_event
    ).respond_with_data("Done")
    with httpserver.wait(raise_assertions=True, stop_on_nohandler=True, timeout=2):
        result = client.simulate_post(
            "/api/v1/insights/annotate",
            params={
                "insight_id": insight_id,
                "annotation": 0,
                "device_id": "test-device",
                "server_type": "off",
            },
            headers={
                "Authorization": "Basic " + base64.b64encode(b"a:b").decode("ascii")
            },
        )
    assert result.status_code == 200


def test_annotate_category_with_user_input(client, mocker, peewee_db):
    """We test category insight annotation with user input."""
    # mock because as we validate the insight, we will ask mongo for product
    mocker.patch(
        "robotoff.insights.annotate.get_product", return_value={"categories_tags": []}
    )
    add_category = mocker.patch("robotoff.insights.annotate.add_category")

    with peewee_db:
        insight = ProductInsightFactory(type="category", value_tag="en:seeds")

    # data must be provided when annotation == 2
    result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={"insight_id": str(insight.id), "annotation": 2},
    )
    assert result.status_code == 400
    assert result.json == {
        "description": "`data` must be provided when annotation == 2",
        "title": "400 Bad Request",
    }

    # update must be true when annotation == 2
    result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": str(insight.id),
            "annotation": 2,
            "data": "{}",
            "update": False,
        },
    )
    assert result.status_code == 400
    assert result.json == {
        "description": "`update` must be true when annotation == 2",
        "title": "400 Bad Request",
    }

    # user input during annotation is forbidden for unauthenticated users
    result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": str(insight.id),
            "annotation": 2,
            "data": '{"value_tag": "en:beef"}',
        },
    )
    assert result.status_code == 400
    assert result.json == {
        "description": "`data` cannot be provided when the user is not authenticated",
        "title": "400 Bad Request",
    }

    # authorized annotation with user input
    auth = base64.b64encode(b"a:b").decode("ascii")
    result = client.simulate_post(
        "/api/v1/insights/annotate",
        params={
            "insight_id": str(insight.id),
            "annotation": 2,
            "data": '{"value_tag": "en:beef"}',
        },
        headers={"Authorization": "Basic " + auth},
    )
    assert result.status_code == 200
    assert result.json == {
        "status_code": 12,
        "status": "user_input_updated",
        "description": "the data provided by the user was saved and sent to OFF",
    }
    add_category.assert_called_once()

    with peewee_db:
        updated_insight = ProductInsight.get_or_none(id=insight.id)
        assert updated_insight is not None
        assert updated_insight.value_tag == "en:beef"
        assert updated_insight.data == {
            "original_value_tag": "en:seeds",
            "user_input": True,
        }


def test_prediction_collection_no_result(client):
    result = client.simulate_get("/api/v1/predictions")
    assert result.status_code == 200
    assert result.json == {"count": 0, "predictions": [], "status": "no_predictions"}


def test_prediction_collection_no_filter(client, peewee_db):
    with peewee_db:
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

    with peewee_db:
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


def test_get_unanswered_questions_api_empty(client, peewee_db):
    with peewee_db:
        ProductInsight.delete().execute()  # remove default sample
    result = client.simulate_get("/api/v1/questions/unanswered")

    assert result.status_code == 200
    assert result.json == {"count": 0, "questions": [], "status": "no_questions"}


def test_get_unanswered_questions_api(client, peewee_db):
    with peewee_db:
        ProductInsight.delete().execute()  # remove default sample
        ProductInsightFactory(
            type="category", value_tag="en:apricot", barcode="00000123"
        )
        ProductInsightFactory(type="label", value_tag="en:beer", barcode="00000456")
        ProductInsightFactory(
            type="nutrition", value_tag="en:soups", barcode="00000789"
        )
        ProductInsightFactory(
            type="nutrition", value_tag="en:salad", barcode="00000302"
        )
        ProductInsightFactory(
            type="nutrition", value_tag="en:salad", barcode="00000403"
        )
        ProductInsightFactory(type="category", value_tag="en:soups", barcode="00000194")
        ProductInsightFactory(type="category", value_tag="en:soups", barcode="00000967")
        ProductInsightFactory(type="label", value_tag="en:beer", barcode="00000039")
        ProductInsightFactory(
            type="category", value_tag="en:apricot", barcode="00000492"
        )
        ProductInsightFactory(type="category", value_tag="en:soups", barcode="00000594")
        ProductInsightFactory(
            type="category",
            value_tag="en:apricot",
            barcode="00000780",
            annotation=1,
        )
        ProductInsightFactory(
            type="category", value_tag="en:apricot", barcode="00000983", annotation=0
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


def test_get_unanswered_questions_api_with_country_filter(client, peewee_db):
    with peewee_db:
        ProductInsight.delete().execute()  # remove default sample
        # test for filter with "country"
        ProductInsightFactory(
            type="location",
            value_tag="en:dates",
            barcode="00000032",
            countries=["en:india"],
        )
        ProductInsightFactory(
            type="location",
            value_tag="en:dates",
            barcode="00000033",
            countries=["en:france"],
        )

    result = client.simulate_get(
        "/api/v1/questions/unanswered", params={"countries": "in"}
    )
    assert result.status_code == 200
    data = result.json
    assert len(data) == 3
    assert len(data["questions"]) == 1
    assert data["questions"] == [["en:dates", 1]]
    assert data["status"] == "found"


def test_get_unanswered_questions_pagination(client, peewee_db):
    with peewee_db:
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
    result = client.simulate_get("/api/v1/image_predictions")
    assert result.status_code == 200


def test_image_prediction_collection(client, peewee_db):
    with peewee_db:
        logo_annotation_category_123 = LogoAnnotationFactory(
            barcode="00000123",
            image_prediction__image__barcode="00000123",
            image_prediction__type="category",
        )
        prediction_category_123 = logo_annotation_category_123.image_prediction
        logo_annotation_label_789 = LogoAnnotationFactory(
            barcode="00000789",
            image_prediction__image__barcode="00000789",
            image_prediction__type="label",
        )
        prediction_label_789 = logo_annotation_label_789.image_prediction

        prediction_label_789_no_logo = ImagePredictionFactory(
            image__barcode="00000789", type="label"
        )

    # test with "barcode=123" and "with_logo=True"
    result = client.simulate_get(
        "/api/v1/image_predictions",
        params={
            "barcode": "00000123",
            "with_logo": 1,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 1
    assert data["image_predictions"][0]["id"] == prediction_category_123.id
    assert data["image_predictions"][0]["image"]["barcode"] == "00000123"

    # test with "type=label" and "with_logo=True"
    result = client.simulate_get(
        "/api/v1/image_predictions",
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
        "/api/v1/image_predictions",
        params={
            "barcode": "00000456",
            "with_logo": 1,
        },
    )

    assert result.status_code == 200
    data = result.json
    assert data["count"] == 0
    assert data["image_predictions"] == []

    # test with "type=label" and "with_logo=False"
    result = client.simulate_get(
        "/api/v1/image_predictions",
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


def test_logo_annotation_collection_api(client, peewee_db):
    with peewee_db:
        LogoAnnotation.delete().execute()  # remove default sample
        annotation_123_1 = LogoAnnotationFactory(
            barcode="00000123",
            image_prediction__image__barcode="00000123",
            annotation_value_tag="etorki",
            annotation_type="brand",
        )
        annotation_123_2 = LogoAnnotationFactory(
            barcode="00000123",
            image_prediction__image__barcode="00000123",
            annotation_value_tag="etorki",
            annotation_type="brand",
        )
        annotation_295 = LogoAnnotationFactory(
            barcode="00000295",
            image_prediction__image__barcode="00000295",
            annotation_value_tag="cheese",
            annotation_type="dairies",
        )
        annotation_789 = LogoAnnotationFactory(
            barcode="00000789",
            image_prediction__image__barcode="00000789",
            annotation_value_tag="creme",
            annotation_type="dairies",
        )
        annotation_306 = LogoAnnotationFactory(
            barcode="00000306",
            image_prediction__image__barcode="00000306",
            annotation_value_tag="yoghurt",
            annotation_type="dairies",
        )
        annotation_604 = LogoAnnotationFactory(
            barcode="00000604",
            image_prediction__image__barcode="00000604",
            annotation_value_tag="meat",
            annotation_type="category",
        )

    # test with "barcode"

    result = client.simulate_get(
        "/api/v1/annotation/collection",
        params={
            "barcode": "00000123",
        },
    )
    assert result.status_code == 200
    data = result.json
    assert data["count"] == 2
    annotation_data = sorted(data["annotation"], key=lambda d: d["id"])
    assert annotation_data[0]["id"] == annotation_123_1.id
    assert annotation_data[1]["id"] == annotation_123_2.id
    assert annotation_data[0]["image_prediction"]["image"]["barcode"] == "00000123"
    assert annotation_data[1]["image_prediction"]["image"]["barcode"] == "00000123"
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
    assert data["annotation"][0]["image_prediction"]["image"]["barcode"] == "00000295"
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
    assert annotations[0]["image_prediction"]["image"]["barcode"] == "00000295"
    assert annotations[1]["id"] == annotation_789.id
    assert annotations[1]["image_prediction"]["image"]["barcode"] == "00000789"
    assert annotations[2]["id"] == annotation_306.id
    assert annotations[2]["image_prediction"]["image"]["barcode"] == "00000306"
    assert annotations[3]["id"] == annotation_604.id
    assert annotations[3]["image_prediction"]["image"]["barcode"] == "00000604"


def test_logo_annotation_collection_pagination(client, peewee_db):
    with peewee_db:
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


def test_predict_lang_invalid_params(client, mocker):
    mocker.patch(
        "robotoff.app.api.predict_lang",
        return_value=[],
    )
    # no text
    result = client.simulate_get("/api/v1/predict/lang", params={"k": 2})
    assert result.status_code == 400
    assert result.json == {
        "description": "1 validation error: [{'type': 'missing', 'loc': ('text',), 'msg': 'Field required', 'input': {'k': '2'}}]",
        "title": "400 Bad Request",
    }

    # invalid k and threshold parameters
    result = client.simulate_get(
        "/api/v1/predict/lang",
        params={"text": "test", "k": "invalid", "threshold": 1.05},
    )
    assert result.status_code == 400
    assert result.json == {
        "description": "2 validation errors: [{'type': 'int_parsing', 'loc': ('k',), 'msg': 'Input should be a valid integer, unable to parse string as an integer', 'input': 'invalid'}, {'type': 'less_than_equal', 'loc': ('threshold',), 'msg': 'Input should be less than or equal to 1', 'input': '1.05', 'ctx': {'le': 1.0}}]",
        "title": "400 Bad Request",
    }


def test_predict_lang(client, mocker):
    mocker.patch(
        "robotoff.app.api.predict_lang",
        return_value=[
            LanguagePrediction("en", 0.9),
            LanguagePrediction("fr", 0.1),
        ],
    )
    expected_predictions = [
        {"lang": "en", "confidence": 0.9},
        {"lang": "fr", "confidence": 0.1},
    ]
    result = client.simulate_get(
        "/api/v1/predict/lang", params={"text": "hello", "k": 2}
    )
    assert result.status_code == 200
    assert result.json == {"predictions": expected_predictions}


def test_predict_lang_http_error(client, mocker):
    mocker.patch(
        "robotoff.app.api.predict_lang",
        side_effect=requests.exceptions.ConnectionError("A connection error occurred"),
    )
    result = client.simulate_get(
        "/api/v1/predict/lang", params={"text": "hello", "k": 2}
    )
    assert result.status_code == 500
    assert result.json == {"title": "500 Internal Server Error"}


def test_predict_product_language(client, peewee_db):
    barcode = "0000123456789"
    prediction_data_1 = {"count": {"en": 10, "fr": 5, "es": 3, "words": 18}}
    prediction_data_2 = {"count": {"en": 2, "fr": 3, "words": 5}}

    with peewee_db:
        PredictionFactory(
            barcode=barcode,
            server_type=ServerType.off.name,
            type=PredictionType.image_lang.name,
            data=prediction_data_1,
            source_image="/000/012/345/6789/2.jpg",
        )
        PredictionFactory(
            barcode=barcode,
            server_type=ServerType.off.name,
            type=PredictionType.image_lang.name,
            data=prediction_data_2,
            source_image="/000/012/345/6789/4.jpg",
        )

    # Send GET request to the API endpoint
    result = client.simulate_get(f"/api/v1/predict/lang/product?barcode={barcode}")

    # Assert the response
    assert result.status_code == 200
    assert result.json == {
        "counts": [
            {"count": 12, "lang": "en"},
            {"count": 8, "lang": "fr"},
            {"count": 3, "lang": "es"},
        ],
        "percent": [
            {"percent": 12 * 100 / 23, "lang": "en"},
            {"percent": 8 * 100 / 23, "lang": "fr"},
            {"percent": 3 * 100 / 23, "lang": "es"},
        ],
        "image_ids": [2, 4],
    }
