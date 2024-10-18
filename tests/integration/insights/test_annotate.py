from unittest.mock import Mock

import pytest

from robotoff.insights.annotate import (
    UPDATED_ANNOTATION_RESULT,
    INVALID_DATA,
    AnnotationResult,
    CategoryAnnotator,
    IngredientSpellcheckAnnotator,
)
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


class TestIngredientSpellcheckAnnotator:

    @pytest.fixture
    def mock_save_ingredients(self, mocker) -> Mock:
        return mocker.patch("robotoff.insights.annotate.save_ingredients")

    @pytest.fixture
    def spellcheck_insight(self):
        return ProductInsightFactory(
            type="ingredient_spellcheck",
            data={
                "original": "List of ingredient",
                "correction": "List fo ingredients",
            },
        )

    def test_process_annotation(
        self,
        mock_save_ingredients: Mock,
        spellcheck_insight: ProductInsightFactory,
    ):
        user_data = {"annotation": "List of ingredients"}
        annotation_result = IngredientSpellcheckAnnotator.process_annotation(
            insight=spellcheck_insight,
            data=user_data,
        )
        assert annotation_result == UPDATED_ANNOTATION_RESULT
        assert "annotation" in spellcheck_insight.data
        mock_save_ingredients.assert_called()

    @pytest.mark.parametrize(
        "user_data",
        [{}, {"annotation": "List of ingredients", "wrong_key": "wrong_item"}],
    )
    def test_process_annotation_invalid_data(
        self,
        user_data: dict,
        mock_save_ingredients: Mock,
        spellcheck_insight: ProductInsightFactory,
    ):
        annotation_result = IngredientSpellcheckAnnotator.process_annotation(
            insight=spellcheck_insight,
            data=user_data,
        )
        assert annotation_result == INVALID_DATA
        mock_save_ingredients.assert_not_called()

    def test_process_annotate_no_user_data(
        self,
        mock_save_ingredients: Mock,
        spellcheck_insight: ProductInsightFactory,
    ):
        annotation_result = IngredientSpellcheckAnnotator.process_annotation(
            insight=spellcheck_insight,
        )
        assert annotation_result == UPDATED_ANNOTATION_RESULT
        assert "annotation" not in spellcheck_insight.data
        mock_save_ingredients.assert_called()
