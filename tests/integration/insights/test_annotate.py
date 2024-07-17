import pytest

from robotoff.insights.annotate import AnnotationResult, CategoryAnnotator
from robotoff.models import ProductInsight

from ..models_utils import ProductInsightFactory, clean_db


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        # clean db
        clean_db()
        # Run the test case.
        yield
        clean_db()


def test_annotation_fails_is_rolledback(mocker):
    annotator = CategoryAnnotator  # should be enough to test with one annotator

    # make it raise
    mocked = mocker.patch.object(
        annotator, "process_annotation", side_effect=Exception("Blah")
    )
    insight = ProductInsightFactory()
    with pytest.raises(Exception):
        annotator().annotate(insight=insight, annotation=1)
    insight = ProductInsight.get(id=insight.id)
    # unchanged
    assert insight.completed_at is None
    assert insight.annotation is None
    # while process_annotation was called
    assert mocked.called


class TestCategoryAnnotator:
    def test_process_annotation(self, mocker):
        insight = ProductInsightFactory(type="category", value_tag="en:cookies")
        add_category_mocked = mocker.patch("robotoff.insights.annotate.add_category")
        get_product_mocked = mocker.patch(
            "robotoff.insights.annotate.get_product", return_value={}
        )
        result = CategoryAnnotator.process_annotation(insight, is_vote=False)
        add_category_mocked.assert_called_once()
        get_product_mocked.assert_called_once()
        assert result == AnnotationResult(
            status_code=2,
            status="updated",
            description="the annotation was saved and sent to OFF",
        )

    def test_process_annotation_with_user_input_data(self, mocker):
        original_value_tag = "en:cookies"
        insight = ProductInsightFactory(
            type="category", value_tag=original_value_tag, data={}
        )
        user_data = {"value_tag": "en:cookie-dough"}
        add_category_mocked = mocker.patch("robotoff.insights.annotate.add_category")
        get_product_mocked = mocker.patch(
            "robotoff.insights.annotate.get_product", return_value={}
        )
        result = CategoryAnnotator.process_annotation(insight, user_data, is_vote=False)
        add_category_mocked.assert_called_once()
        get_product_mocked.assert_called_once()
        assert result == AnnotationResult(
            status_code=12,
            status="user_input_updated",
            description="the data provided by the user was saved and sent to OFF",
        )
        assert insight.value_tag == user_data["value_tag"]
        assert insight.data == {
            "user_input": True,
            "original_value_tag": original_value_tag,
        }

    @pytest.mark.parametrize("user_data", [{}, {"invalid_key": "v"}, {"value_tag": 1}])
    def test_process_annotation_with_invalid_user_input_data(self, user_data, mocker):
        original_value_tag = "en:cookies"
        insight = ProductInsightFactory(
            type="category", value_tag=original_value_tag, data={}
        )
        add_category_mocked = mocker.patch("robotoff.insights.annotate.add_category")
        get_product_mocked = mocker.patch(
            "robotoff.insights.annotate.get_product", return_value={}
        )
        result = CategoryAnnotator.process_annotation(insight, user_data, is_vote=False)
        assert not add_category_mocked.called
        get_product_mocked.assert_called_once()
        assert result == AnnotationResult(
            status_code=11,
            status="error_invalid_data",
            description="`data` is invalid, expected a single `value_tag` string field with the category tag",
        )
