import base64
from datetime import datetime
from typing import Any

import falcon.testing
import pytest

import robotoff.insights.importer
import robotoff.taxonomy
from robotoff.app.api import api
from robotoff.insights.annotate import UPDATED_ANNOTATION_RESULT
from robotoff.models import LogoAnnotation, Prediction, ProductInsight
from robotoff.products import Product

from .models_utils import LogoAnnotationFactory, clean_db


@pytest.fixture()
def client():
    return falcon.testing.TestClient(api)


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        clean_db()
        # Run the test case.
    yield

    with peewee_db:
        clean_db()


def _fake_store(monkeypatch, barcode):
    monkeypatch.setattr(
        robotoff.insights.importer,
        "get_product_store",
        lambda: {
            barcode: Product(
                {
                    "code": barcode,  # needed to validate brand/label
                    # needed to validate image
                    "images": {
                        "2": {"rev": 1, "uploaded_t": datetime.utcnow().timestamp()}
                    },
                }
            )
        },
    )


@pytest.fixture
def fake_taxonomy(monkeypatch):
    def fetch_taxonomy_mock(url: str, *args, **kwargs):
        data: Any = None
        if "/brands." in url:
            data = {"en:etorki": {"name": {"en": "Etorki"}}}
        elif "/labels." in url:
            data = {
                "en:organic": {
                    "synonyms": {"fr": ["Bio"]},
                    "children": ["en:eu-organic"],
                },
                "en:eu-organic": {
                    "wikidata": {"en": "Q380448"},
                    "parents": ["en:organic"],
                },
            }
        return robotoff.taxonomy.Taxonomy.from_dict(data) if data else None

    monkeypatch.setattr(
        robotoff.taxonomy,
        "fetch_taxonomy",
        fetch_taxonomy_mock,
    )


_AUTH_HEADER = {"Authorization": "Basic " + base64.b64encode(b"a:b").decode("ascii")}


def test_logo_annotation_empty_payload(client):
    """A JSON payload with 'annotations' key must be provided."""
    result = client.simulate_post(
        "/api/v1/images/logos/annotate",
        json={
            "withCredentials": True,
        },
        headers=_AUTH_HEADER,
    )
    assert result.status_code == 400
    assert result.json == {
        "description": "'annotations' is a required property",
        "title": "Request data failed validation",
    }


def test_logo_annotation_invalid_logo_type(client):
    """The logo type must be valid."""
    result = client.simulate_post(
        "/api/v1/images/logos/annotate",
        json={
            "withCredentials": True,
            "annotations": [
                {"logo_id": 10, "value": "etorki", "type": "INVALID_TYPE"},
                {"logo_id": 11, "value": "etorki", "type": "brand"},
            ],
        },
        headers=_AUTH_HEADER,
    )
    assert result.status_code == 400
    assert result.json.get("title") == "Request data failed validation"


@pytest.mark.parametrize("logo_type", ["brand", "category", "label", "store"])
def test_logo_annotation_missing_value_when_required(logo_type, client):
    """A `value` is expected for some logo type."""
    result = client.simulate_post(
        "/api/v1/images/logos/annotate",
        json={
            "withCredentials": True,
            "annotations": [{"logo_id": 10, "type": logo_type}],
        },
        headers=_AUTH_HEADER,
    )
    assert result.status_code == 400
    assert result.json == {
        "description": "'value' is a required property",
        "title": "Request data failed validation",
    }


def test_logo_annotation_incorrect_value_label_type(client, peewee_db):
    """A language-prefixed value is expected for label type."""

    with peewee_db:
        ann = LogoAnnotationFactory(
            image_prediction__image__source_image="/images/2.jpg",
            annotation_type=None,
        )
    result = client.simulate_post(
        "/api/v1/images/logos/annotate",
        json={
            "withCredentials": True,
            "annotations": [
                {"logo_id": ann.id, "type": "label", "value": "eu-organic"}
            ],
        },
        headers=_AUTH_HEADER,
    )
    assert result.status_code == 400
    assert result.json == {
        "description": "language-prefixed value are required for label type (here: eu-organic)",
        "title": "400 Bad Request",
    }


def test_logo_annotation_brand(client, peewee_db, monkeypatch, mocker, fake_taxonomy):
    with peewee_db:
        ann = LogoAnnotationFactory(
            image_prediction__image__source_image="/images/2.jpg",
            annotation_type=None,
        )
    barcode = ann.image_prediction.image.barcode
    _fake_store(monkeypatch, barcode)
    mocker.patch(
        "robotoff.brands.get_brand_prefix", return_value={("Etorki", "0000000xxxxxx")}
    )
    mocker.patch("robotoff.logos.annotate", return_value=UPDATED_ANNOTATION_RESULT)
    start = datetime.utcnow()
    result = client.simulate_post(
        "/api/v1/images/logos/annotate",
        json={
            "withCredentials": True,
            "annotations": [{"logo_id": ann.id, "value": "etorki", "type": "brand"}],
        },
        headers=_AUTH_HEADER,
    )
    end = datetime.utcnow()
    assert result.status_code == 200
    assert result.json == {"created insights": 1}

    with peewee_db:
        ann = LogoAnnotation.get(LogoAnnotation.id == ann.id)
    assert ann.annotation_type == "brand"
    assert ann.annotation_value == "etorki"
    assert ann.annotation_value_tag == "etorki"
    assert ann.taxonomy_value == "Etorki"
    assert ann.username == "a"
    assert start <= ann.completed_at <= end
    # we generate a prediction

    with peewee_db:
        predictions = list(Prediction.select().filter(barcode=barcode).execute())
    assert len(predictions) == 1
    (prediction,) = predictions
    assert prediction.type == "brand"
    assert prediction.data == {
        "logo_id": ann.id,
        "username": "a",
        "is_annotation": True,
        "bounding_box": [0.4, 0.4, 0.6, 0.6],
    }
    assert prediction.confidence == 1.0
    assert prediction.value == "Etorki"
    assert prediction.value_tag == "Etorki"
    assert prediction.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert prediction.automatic_processing is False
    # We check that this prediction in turn generates an insight

    with peewee_db:
        insights = list(ProductInsight.select().filter(barcode=barcode).execute())
    assert len(insights) == 1
    (insight,) = insights
    assert insight.type == "brand"
    assert insight.data == {
        "logo_id": ann.id,
        "username": "a",
        "is_annotation": True,
        "bounding_box": [0.4, 0.4, 0.6, 0.6],
    }
    assert insight.confidence == 1.0
    assert insight.value == "Etorki"
    assert insight.value_tag == "Etorki"
    assert insight.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert insight.automatic_processing is False
    assert insight.username == "a"
    assert insight.completed_at is None  # we did not run annotate yet


def test_logo_annotation_label(client, peewee_db, monkeypatch, fake_taxonomy, mocker):
    """This test will check that, given an image with a logo above the confidence threshold,
    that is then fed into the ANN logos and labels model, we annotate properly a product.
    """
    with peewee_db:
        ann = LogoAnnotationFactory(
            image_prediction__image__source_image="/images/2.jpg", annotation_type=None
        )
    barcode = ann.image_prediction.image.barcode
    _fake_store(monkeypatch, barcode)
    mocker.patch("robotoff.logos.annotate", return_value=UPDATED_ANNOTATION_RESULT)
    start = datetime.utcnow()
    result = client.simulate_post(
        "/api/v1/images/logos/annotate",
        json={
            "withCredentials": True,
            "annotations": [
                {"logo_id": ann.id, "value": "en:eu-organic", "type": "label"}
            ],
        },
        headers=_AUTH_HEADER,
    )
    end = datetime.utcnow()
    assert result.status_code == 200
    assert result.json == {"created insights": 1}
    with peewee_db:
        ann = LogoAnnotation.get(LogoAnnotation.id == ann.id)
    assert ann.annotation_type == "label"
    assert ann.annotation_value == "en:eu-organic"
    assert ann.annotation_value_tag == "en:eu-organic"
    assert ann.taxonomy_value == "en:eu-organic"
    assert ann.username == "a"
    assert start <= ann.completed_at <= end
    # we generate a prediction
    with peewee_db:
        predictions = list(Prediction.select().filter(barcode=barcode).execute())
    assert len(predictions) == 1
    (prediction,) = predictions
    assert prediction.type == "label"
    assert prediction.data == {
        "logo_id": ann.id,
        "username": "a",
        "is_annotation": True,
        "bounding_box": [0.4, 0.4, 0.6, 0.6],
    }
    assert prediction.confidence == 1.0
    assert prediction.value is None
    assert prediction.value_tag == "en:eu-organic"
    assert prediction.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert prediction.automatic_processing is False
    # We check that this prediction in turn generates an insight
    with peewee_db:
        insights = list(ProductInsight.select().filter(barcode=barcode).execute())
    assert len(insights) == 1
    (insight,) = insights
    assert insight.type == "label"
    assert insight.data == {
        "logo_id": ann.id,
        "username": "a",
        "is_annotation": True,
        "bounding_box": [0.4, 0.4, 0.6, 0.6],
    }
    assert insight.confidence == 1.0
    assert insight.value is None
    assert insight.value_tag == "en:eu-organic"
    assert insight.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert insight.automatic_processing is False
    assert insight.username == "a"
    assert insight.completed_at is None
