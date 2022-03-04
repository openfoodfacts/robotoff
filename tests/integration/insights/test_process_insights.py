from datetime import datetime, timedelta

import pytest

from robotoff import settings
from robotoff.models import ProductInsight
from robotoff.scheduler import process_insights

from ..models_utils import ProductInsightFactory


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    # clean db
    ProductInsight.delete().execute()
    # Run the test case.
    yield
    # Tear down.
    ProductInsight.delete().execute()


# global for generating items
_id_count = 0


def _create_insight(**kwargs):
    data = dict(
        {
            "data": {"notify": False},  # we do not test notification
            "type": "category",
            "value_tag": "en:Salmons",
            "automatic_processing": True,
            "process_after": datetime.now() - timedelta(minutes=12),
            "n_votes": 3,
        },
        **kwargs,
    )
    insight = ProductInsightFactory(**data)
    return insight.id, insight.barcode


def test_process_insight_category(mocker):
    mocker.patch(
        "robotoff.insights.annotate.get_product", return_value={"categories_tags": []}
    )
    mock = mocker.patch("robotoff.off.update_product")
    # a processed insight exists
    date0 = datetime.now() - timedelta(minutes=10)
    id0, code0 = _create_insight(type="category", completed_at=date0, annotation=1)
    # an insight to be processed
    id1, code1 = _create_insight(type="category")
    # run process
    process_insights()
    # insight 0 not touched
    assert ProductInsight.get(id=id0).completed_at == date0
    # insight 1 processed
    insight = ProductInsight.get(id=id1)
    assert insight.completed_at is not None
    assert insight.completed_at <= datetime.now()
    assert insight.annotation == 1
    # update_product calledfor item 1
    mock.assert_called_once_with(
        {
            "code": code1,
            "add_categories": "en:Salmons",
            "comment": f"[robotoff] Adding category 'en:Salmons', ID: {id1}",
        },
        auth=None,
        server_domain=settings.OFF_SERVER_DOMAIN,
    )


def test_process_insight_category_existing(mocker):
    mocker.patch(
        "robotoff.insights.annotate.get_product",
        return_value={"categories_tags": ["en:Salmons"]},
    )
    mock = mocker.patch("robotoff.off.update_product")
    # an insight to be processed
    id1, code1 = _create_insight(type="category")
    # run process
    process_insights()
    # insight processed
    insight = ProductInsight.get(id=id1)
    assert insight.completed_at is not None
    assert insight.completed_at <= datetime.now()
    assert insight.annotation == 1
    # but update_product wasn't called
    mock.assert_not_called()


def test_process_insight_non_existing_product(mocker):
    mocker.patch("robotoff.insights.annotate.get_product", return_value=None)
    mock = mocker.patch("robotoff.off.update_product")
    # an insight to be processed
    id1, code1 = _create_insight(type="category")
    # run process
    process_insights()
    # insight processed
    insight = ProductInsight.get(id=id1)
    assert insight.completed_at is not None
    assert insight.completed_at <= datetime.now()
    assert insight.annotation == 1
    # but update_product wasn't called
    mock.assert_not_called()


def test_process_insight_update_product_raises(mocker):
    def raise_for_salmons(params, *args, **kwargs):
        if "en:Salmons" in params.values():
            raise Exception("Boom !")
        else:
            return

    mocker.patch(
        "robotoff.insights.annotate.get_product", return_value={"categories_tags": []}
    )
    mock = mocker.patch("robotoff.off.update_product", side_effect=raise_for_salmons)
    # an insight to be processed, that will raise
    id1, code1 = _create_insight(type="category")
    # add another insight that should pass
    id2, code2 = _create_insight(type="category", value_tag="en:Tuna")
    # run process
    start = datetime.utcnow()
    process_insights()
    end = datetime.utcnow()
    # insight1 not marked processed
    insight = ProductInsight.get(id=id1)
    assert insight.completed_at is None
    assert insight.annotation is None
    # but update_product was called
    mock.assert_any_call(
        {
            "code": code1,
            "add_categories": "en:Salmons",
            "comment": f"[robotoff] Adding category 'en:Salmons', ID: {id1}",
        },
        auth=None,
        server_domain=settings.OFF_SERVER_DOMAIN,
    )
    # insight2 processed
    # and update_product was called
    insight = ProductInsight.get(id=id2)
    assert insight.completed_at is not None
    assert start < insight.completed_at < end
    assert insight.annotation == 1
    mock.assert_any_call(
        {
            "code": code2,
            "add_categories": "en:Tuna",
            "comment": f"[robotoff] Adding category 'en:Tuna', ID: {id2}",
        },
        auth=None,
        server_domain=settings.OFF_SERVER_DOMAIN,
    )
    # we add only two calls
    assert mock.call_count == 2


def test_process_insight_same_product(mocker):
    mocker.patch(
        "robotoff.insights.annotate.get_product",
        return_value={"categories_tags": ["en:Salmons"]},
    )
    mock = mocker.patch("robotoff.off.update_product")
    # an insight to be processed but already there
    id1, code1 = _create_insight(type="category", value_tag="en:Salmons")
    # a new category
    id2, code2 = _create_insight(type="category", value_tag="en:Big fish")
    # another new category
    id3, code3 = _create_insight(type="category", value_tag="en:Smoked Salmon")
    # run process
    process_insights()
    # insights processed
    for id_ in [id1, id2, id3]:
        insight = ProductInsight.get(id=id_)
        assert insight.completed_at is not None
        assert insight.completed_at <= datetime.now()
        assert insight.annotation == 1
    # update_product was called twice
    assert mock.call_count == 2
    mock.assert_any_call(
        {
            "code": code2,
            "add_categories": "en:Big fish",
            "comment": f"[robotoff] Adding category 'en:Big fish', ID: {id2}",
        },
        auth=None,
        server_domain=settings.OFF_SERVER_DOMAIN,
    )
    mock.assert_any_call(
        {
            "code": code3,
            "add_categories": "en:Smoked Salmon",
            "comment": f"[robotoff] Adding category 'en:Smoked Salmon', ID: {id3}",
        },
        auth=None,
        server_domain=settings.OFF_SERVER_DOMAIN,
    )
