from datetime import datetime

import robotoff.insights.importer
import robotoff.taxonomy
from robotoff import settings
from robotoff.logos import generate_insights_from_annotated_logos_job
from robotoff.models import Prediction, ProductInsight
from robotoff.off import OFFAuthentication
from robotoff.products import Product

from .models_utils import LogoAnnotationFactory


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


def test_generate_insights_from_annotated_logos_job(peewee_db, monkeypatch, mocker):
    barcode = "0000000000001"
    _fake_store(monkeypatch, barcode)
    mocker.patch(
        "robotoff.brands.get_brand_prefix", return_value={("Etorki", "0000000xxxxxx")}
    )
    mocker.patch("robotoff.insights.annotate.add_brand", return_value=None)
    mocker.patch(
        "robotoff.insights.annotate.get_product",
        return_value={"barcode": barcode, "brands_tags": []},
    )
    source_image = "/000/000/000/0001/2.jpg"
    username = "a"
    with peewee_db:
        ann = LogoAnnotationFactory(
            barcode=barcode,
            source_image=source_image,
            annotation_type="brand",
            annotation_value="etorki",
            annotation_value_tag="etorki",
            taxonomy_value="Etorki",
            username=username,
        )

    start = datetime.utcnow()
    generate_insights_from_annotated_logos_job(
        [ann.id],
        settings.BaseURLProvider.server_domain(),
        OFFAuthentication(username=username, password=username),
    )
    end = datetime.utcnow()
    # we generate a prediction

    with peewee_db:
        predictions = list(Prediction.select().where(Prediction.barcode == barcode))
    assert len(predictions) == 1
    (prediction,) = predictions
    assert prediction.type == "brand"
    assert prediction.data == {
        "logo_id": ann.id,
        "username": username,
        "is_annotation": True,
        "bounding_box": [0.4, 0.4, 0.6, 0.6],
    }
    assert prediction.confidence == 1.0
    assert prediction.value == "Etorki"
    assert prediction.value_tag == "etorki"
    assert prediction.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert prediction.automatic_processing is False
    # We check that this prediction in turn generates an insight

    with peewee_db:
        insights = list(
            ProductInsight.select().where(ProductInsight.barcode == barcode)
        )
    assert len(insights) == 1
    (insight,) = insights
    assert insight.type == "brand"
    assert insight.data == {
        "logo_id": ann.id,
        "username": username,
        "is_annotation": True,
        "bounding_box": [0.4, 0.4, 0.6, 0.6],
    }
    assert insight.confidence == 1.0
    assert insight.value == "Etorki"
    assert insight.value_tag == "etorki"
    assert insight.predictor == "universal-logo-detector"
    assert start <= prediction.timestamp <= end
    assert insight.automatic_processing is False
    assert insight.username == "a"
    assert insight.annotation == 1
    assert insight.annotated_result == 2
    assert isinstance(insight.completed_at, datetime)
