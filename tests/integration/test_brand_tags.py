import dataclasses
import importlib

import pytest
from falcon import testing
from peewee_migrate import Migrator

from robotoff.app.api import api
from robotoff.app.core import get_insights, get_predictions
from robotoff.insights.importer import BrandInsightImporter, import_product_predictions
from robotoff.models import AnnotationVote, ProductInsight
from robotoff.models import Prediction as PredictionModel
from robotoff.products import DBProductStore, Product
from robotoff.types import (
    InsightType,
    Prediction,
    PredictionType,
    ProductIdentifier,
    ServerType,
)

from .models_utils import (
    AnnotationVoteFactory,
    PredictionFactory,
    ProductInsightFactory,
    clean_db,
)


@pytest.fixture(autouse=True)
def database(peewee_db):
    with peewee_db:
        clean_db()
        yield peewee_db
        clean_db()


def migrate_brand_tags(database):
    migration = importlib.import_module("migrations.010_normalize_brand_value_tags")
    migrator = Migrator(database)
    migration.migrate(migrator, database)
    migrator()


@pytest.mark.parametrize("factory", [PredictionFactory, ProductInsightFactory])
def test_migration_preserves_records_and_is_idempotent(database, factory):
    records = [
        factory(type=InsightType.brand.name, value_tag=tag, value="Display name")
        for tag in ["nestle", "xx:nestle", None, "", "en:nestle", "xx:"]
    ]
    other = factory(type=InsightType.label.name, value_tag="nestle")
    before = [record.to_dict() for record in records]
    if factory == ProductInsightFactory:
        records[0].annotation = 1
        records[0].n_votes = 1
        records[0].save()
        before[0] = records[0].to_dict()
        vote = AnnotationVoteFactory(insight_id=records[0])

    for _ in range(2):
        migrate_brand_tags(database)
        for record, original in zip(records, before, strict=True):
            expected = {**original}
            if original["value_tag"] == "nestle":
                expected["value_tag"] = "xx:nestle"
            assert type(record).get_by_id(record.id).to_dict() == expected
        assert type(other).get_by_id(other.id).value_tag == "nestle"
        if factory == ProductInsightFactory:
            assert AnnotationVote.get_by_id(vote.id).insight_id_id == records[0].id


@pytest.mark.parametrize("tag", ["nestle", "xx:nestle"])
def test_import_predictions_normalizes_before_duplicate_detection(tag):
    prediction = Prediction(
        type=PredictionType.brand,
        barcode="1234567891234",
        value_tag=tag,
        value="Nestlé",
        predictor="google-cloud-vision",
    )
    alternate = dataclasses.replace(prediction, value_tag="xx:nestle")
    assert import_product_predictions(
        prediction.barcode, ServerType.off, [prediction, alternate]
    ) == (1, 0)
    assert import_product_predictions(
        prediction.barcode, ServerType.off, [prediction]
    ) == (0, 0)
    assert PredictionModel.get().value_tag == "xx:nestle"
    assert prediction.value_tag == tag


@pytest.mark.parametrize("tag", ["nestle", "xx:nestle"])
def test_import_brand_insight_keeps_existing_id_and_votes(mocker, tag):
    product_id = ProductIdentifier("1234567891234", ServerType.off)
    store = mocker.MagicMock(spec=DBProductStore)
    store.__getitem__.return_value = Product({"code": product_id.barcode})
    prediction = Prediction(
        type=PredictionType.brand,
        barcode=product_id.barcode,
        value_tag=tag,
        value="Nestlé",
        predictor="google-cloud-vision",
    )
    BrandInsightImporter.import_insights(product_id, [prediction], store)
    insight = ProductInsight.get()
    assert insight.value_tag == "xx:nestle"
    vote = AnnotationVoteFactory(insight_id=insight)
    BrandInsightImporter.import_insights(product_id, [prediction], store)
    assert ProductInsight.select().count() == 1
    assert ProductInsight.get().id == insight.id
    assert AnnotationVote.get_by_id(vote.id).insight_id_id == insight.id


@pytest.mark.parametrize("value_tag", ["nestle", "xx:nestle"])
def test_migrated_brands_have_canonical_api_responses(database, mocker, value_tag):
    mocker.patch("robotoff.insights.question.get_product", return_value=None)
    for index, tag in enumerate(["nestle", "xx:nestle"]):
        ProductInsightFactory(
            type=InsightType.brand.name,
            barcode=str(index + 1),
            value_tag=tag,
            value="Nestlé",
        )
        PredictionFactory(type=PredictionType.brand.name, value_tag=tag)
    migrate_brand_tags(database)
    client = testing.TestClient(api)
    for endpoint, key in [
        ("/api/v1/questions", "questions"),
        ("/api/v1/insights", "insights"),
        ("/api/v1/predictions", "predictions"),
    ]:
        response = client.simulate_get(endpoint, params={"value_tag": value_tag})
        assert response.status_code == 200
        assert response.json["count"] == 2
        assert len(response.json[key]) == 2
        assert {row["value_tag"] for row in response.json[key]} == {"xx:nestle"}

    response = client.simulate_get(
        "/api/v1/questions/unanswered", params={"type": InsightType.brand.name}
    )
    assert response.status_code == 200
    assert response.json["count"] == 2
    assert response.json["questions"] == [["xx:nestle", 2]]


@pytest.mark.parametrize(
    "factory,getter",
    [(ProductInsightFactory, get_insights), (PredictionFactory, get_predictions)],
)
@pytest.mark.parametrize("value_tag", ["nestle", "xx:nestle", "en:nestle", "xx:"])
def test_filters_preserve_exact_matching_for_other_types(factory, getter, value_tag):
    brand = factory(type=InsightType.brand.name, value_tag="xx:nestle")
    expected = {brand.id} if value_tag in ("nestle", "xx:nestle") else set()
    for tag in ["nestle", "xx:nestle", "en:nestle", "xx:"]:
        record = factory(type=InsightType.label.name, value_tag=tag)
        if tag == value_tag:
            expected.add(record.id)
    factory(type=InsightType.brand.name, value_tag="xx:nestle", server_type="obf")
    records = list(getter(server_type=ServerType.off, value_tag=value_tag))
    assert {record.id for record in records} == expected
    assert getter(server_type=ServerType.off, value_tag=value_tag, count=True) == len(
        expected
    )
