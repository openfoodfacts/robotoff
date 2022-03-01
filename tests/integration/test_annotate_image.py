import base64
from datetime import datetime
from typing import Any

import falcon.testing
import pytest

import robotoff.insights.importer
import robotoff.taxonomy
from robotoff.app.api import api
from robotoff.brands import BRAND_PREFIX_STORE
from robotoff.models import LogoAnnotation, Prediction, ProductInsight
from robotoff.products import Product

from .models_utils import LogoAnnotationFactory, clean_db


@pytest.fixture()
def client():
    return falcon.testing.TestClient(api)


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    clean_db()
    # Run the test case.
    yield
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


def test_image_brand_annotation(client, monkeypatch, fake_taxonomy):
    ann = LogoAnnotationFactory(image_prediction__image__source_image="/images/2.jpg")
    barcode = ann.image_prediction.image.barcode
    _fake_store(monkeypatch, barcode)
    monkeypatch.setattr(
        BRAND_PREFIX_STORE, "get", lambda: {("Etorki", "0000000xxxxxx")}
    )
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
    ann = LogoAnnotation.get(LogoAnnotation.id == ann.id)
    assert ann.annotation_type == "brand"
    assert ann.annotation_value == "etorki"
    assert ann.annotation_value_tag == "etorki"
    assert ann.taxonomy_value == "Etorki"
    assert ann.username == "a"
    assert start <= ann.completed_at <= end
    # we generate a prediction
    predictions = list(Prediction.select().filter(barcode=barcode).execute())
    assert len(predictions) == 1
    (prediction,) = predictions
    assert prediction.type == "brand"
    assert prediction.data == {
        "logo_id": ann.id,
        "confidence": 1.0,
        "username": "a",
        "is_annotation": True,
        "notify": True,
    }
    assert prediction.value == "Etorki"
    assert prediction.value_tag == "Etorki"
    assert prediction.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert prediction.automatic_processing
    # that in turn generated an insight
    insights = list(ProductInsight.select().filter(barcode=barcode).execute())
    assert len(insights) == 1
    (insight,) = insights
    assert insight.type == "brand"
    assert insight.data == {
        "logo_id": ann.id,
        "confidence": 1.0,
        "username": "a",
        "is_annotation": True,
        "notify": True,
    }
    assert insight.value == "Etorki"
    assert insight.value_tag == "Etorki"
    assert insight.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert insight.automatic_processing
    assert insight.username == "a"
    assert insight.completed_at is None  # we did not run annotate yet


def test_image_label_annotation(client, monkeypatch, fake_taxonomy):
    ann = LogoAnnotationFactory(image_prediction__image__source_image="/images/2.jpg")
    barcode = ann.image_prediction.image.barcode
    _fake_store(monkeypatch, barcode)
    start = datetime.utcnow()
    result = client.simulate_post(
        "/api/v1/images/logos/annotate",
        json={
            "withCredentials": True,
            "annotations": [
                {"logo_id": ann.id, "value": "EU Organic", "type": "label"}
            ],
        },
        headers=_AUTH_HEADER,
    )
    end = datetime.utcnow()
    assert result.status_code == 200
    assert result.json == {"created insights": 1}
    ann = LogoAnnotation.get(LogoAnnotation.id == ann.id)
    assert ann.annotation_type == "label"
    assert ann.annotation_value == "EU Organic"
    assert ann.annotation_value_tag == "eu-organic"
    assert ann.taxonomy_value == "en:eu-organic"
    assert ann.username == "a"
    assert start <= ann.completed_at <= end
    # we generate a prediction
    predictions = list(Prediction.select().filter(barcode=barcode).execute())
    assert len(predictions) == 1
    (prediction,) = predictions
    assert prediction.type == "label"
    assert prediction.data == {
        "logo_id": ann.id,
        "confidence": 1.0,
        "username": "a",
        "is_annotation": True,
        "notify": True,
    }
    assert prediction.value is None
    assert prediction.value_tag == "en:eu-organic"
    assert prediction.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert prediction.automatic_processing
    # that in turn generated an insight
    insights = list(ProductInsight.select().filter(barcode=barcode).execute())
    assert len(insights) == 1
    (insight,) = insights
    assert insight.type == "label"
    assert insight.data == {
        "logo_id": ann.id,
        "confidence": 1.0,
        "username": "a",
        "is_annotation": True,
        "notify": True,
    }
    assert insight.value is None
    assert insight.value_tag == "en:eu-organic"
    assert insight.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert insight.automatic_processing
    assert insight.username == "a"
    assert insight.completed_at is None
