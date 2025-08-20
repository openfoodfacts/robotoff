import base64
import datetime
from typing import Any

import falcon.testing
import pytest
from openfoodfacts.types import TaxonomyType

import robotoff.insights.importer
import robotoff.taxonomy
from robotoff.app.api import api
from robotoff.models import LogoAnnotation

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


@pytest.fixture
def fake_taxonomy(monkeypatch):
    def _get_taxonomy_mock(taxonomy_type: TaxonomyType, *args, **kwargs):
        data: Any = None
        if taxonomy_type is TaxonomyType.brand:
            data = {"en:etorki": {"name": {"en": "Etorki"}}}
        elif taxonomy_type is TaxonomyType.label:
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
        "_get_taxonomy",
        _get_taxonomy_mock,
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
    barcode = "0000000000001"
    source_image = "/000/000/000/0001/2.jpg"
    with peewee_db:
        ann = LogoAnnotationFactory(
            barcode=barcode,
            source_image=source_image,
            annotation_type=None,
        )
    mocker.patch("robotoff.app.api.enqueue_job", return_value=None)
    start = datetime.datetime.now()
    result = client.simulate_post(
        "/api/v1/images/logos/annotate",
        json={
            "withCredentials": True,
            "annotations": [{"logo_id": ann.id, "value": "etorki", "type": "brand"}],
        },
        headers=_AUTH_HEADER,
    )
    end = datetime.datetime.now()
    assert result.status_code == 200
    assert result.json == {"annotated": 1}

    with peewee_db:
        ann = LogoAnnotation.get(LogoAnnotation.id == ann.id)
    assert ann.annotation_type == "brand"
    assert ann.annotation_value == "etorki"
    assert ann.annotation_value_tag == "etorki"
    assert ann.taxonomy_value == "Etorki"
    assert ann.username == "a"
    assert start <= ann.completed_at <= end


def test_logo_annotation_label(client, peewee_db, monkeypatch, fake_taxonomy, mocker):
    """This test will check that, given an image with a logo above the
    confidence threshold, that is then fed into the ANN logos and labels model,
    we annotate properly a product.
    """
    barcode = "0000000000001"
    source_image = "/000/000/000/0001/2.jpg"
    with peewee_db:
        ann = LogoAnnotationFactory(
            barcode=barcode, source_image=source_image, annotation_type=None
        )
    mocker.patch("robotoff.app.api.enqueue_job", return_value=None)
    start = datetime.datetime.now()
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
    end = datetime.datetime.now()
    assert result.status_code == 200
    assert result.json == {"annotated": 1}
    with peewee_db:
        ann = LogoAnnotation.get(LogoAnnotation.id == ann.id)
    assert ann.annotation_type == "label"
    assert ann.annotation_value == "en:eu-organic"
    assert ann.annotation_value_tag == "en:eu-organic"
    assert ann.taxonomy_value == "en:eu-organic"
    assert ann.username == "a"
    assert start <= ann.completed_at <= end
