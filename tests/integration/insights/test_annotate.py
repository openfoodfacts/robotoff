from unittest.mock import Mock

import pytest
from openfoodfacts.types import JSONType

from robotoff.insights.annotate import (
    INVALID_DATA,
    UPDATED_ANNOTATION_RESULT,
    AnnotationResult,
    AnnotationStatus,
    CategoryAnnotator,
    ImageOrientationAnnotator,
    IngredientSpellcheckAnnotator,
    NutrientExtractionAnnotator,
)
from robotoff.models import ProductInsight
from robotoff.types import InsightType, ObjectDetectionModel, PredictionType

from ..models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    PredictionFactory,
    ProductInsightFactory,
    clean_db,
)


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


class TestImageOrientationAnnotation:
    def test_rotate_image(self, peewee_db, mocker):
        mock_product = {
            "code": "1234567890123",
            "images": {"1": {"uploaded_t": "1234567890"}, "front_fr": {"imgid": "1"}},
        }
        mock_get_product = mocker.patch(
            "robotoff.insights.annotate.get_product", return_value=mock_product
        )

        mock_response = mocker.MagicMock()
        mock_response.content = b"dummy_image_data"
        mock_get = mocker.patch("requests.get", return_value=mock_response)

        mock_image = mocker.MagicMock()
        mock_image.__enter__.return_value = mock_image
        mock_rotated = mocker.MagicMock()
        mock_image.rotate.return_value = mock_rotated
        mock_image_open = mocker.patch("PIL.Image.open", return_value=mock_image)

        mock_temp_file = mocker.MagicMock()
        mock_temp_file.name = "/tmp/dummy_temp_file.jpg"
        mock_temp_file.__enter__.return_value = mock_temp_file
        mock_named_temp_file = mocker.patch(
            "tempfile.NamedTemporaryFile", return_value=mock_temp_file
        )

        mock_unlink = mocker.patch("os.unlink")
        mock_upload = mocker.patch(
            "robotoff.insights.annotate.upload_image", return_value="10"
        )
        mock_select_rotate = mocker.patch(
            "robotoff.insights.annotate.select_rotate_image"
        )

        insight = ProductInsightFactory(
            type=InsightType.image_orientation.name,
            source_image="/123/456/789/1234/1.jpg",
            data={"rotation": 90, "orientation": "right"},
        )

        result = ImageOrientationAnnotator().annotate(insight=insight, annotation=1)
        assert result.status_code == AnnotationStatus.updated.value

        mock_get_product.assert_called_once()
        mock_get.assert_called_once()
        assert "images.openfoodfacts.org" in mock_get.call_args[0][0]

        mock_image_open.assert_called_once()
        mock_image.rotate.assert_called_once_with(-90, expand=True)

        mock_named_temp_file.assert_called_once()
        mock_unlink.assert_called_once_with("/tmp/dummy_temp_file.jpg")

        mock_upload.assert_called_once()
        mock_select_rotate.assert_called_once()
        assert mock_select_rotate.call_args[1]["image_key"] == "front_fr"
        assert mock_select_rotate.call_args[1]["image_id"] == "10"

    def test_error_invalid_image(self, peewee_db, mocker):
        mock_product = {
            "code": "1234567890123",
            "images": {
                "2": {"uploaded_t": "1234567890"},
            },
        }
        mock_get_product = mocker.patch(
            "robotoff.insights.annotate.get_product", return_value=mock_product
        )

        insight = ProductInsightFactory(
            type=InsightType.image_orientation.name,
            source_image="/123/456/789/1234/1.jpg",
            data={"rotation": 90, "orientation": "right"},
        )

        result = ImageOrientationAnnotator().annotate(insight=insight, annotation=1)
        assert mock_get_product.called
        assert result.status_code == AnnotationStatus.error_invalid_image.value

    def test_error_missing_rotation(self, peewee_db, mocker):
        mock_product = {
            "code": "1234567890123",
            "images": {
                "1": {"uploaded_t": "1234567890"},
            },
        }
        mock_get_product = mocker.patch(
            "robotoff.insights.annotate.get_product", return_value=mock_product
        )

        insight = ProductInsightFactory(
            type=InsightType.image_orientation.name,
            source_image="/123/456/789/1234/1.jpg",
            data={"orientation": "right"},  # Missing rotation
        )

        result = ImageOrientationAnnotator().annotate(insight=insight, annotation=1)
        assert mock_get_product.called
        assert result.status_code == AnnotationStatus.error_invalid_data.value


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

    class TestNutrientExtractionAnnotator:
        SOURCE_IMAGE = "/872/032/603/7888/2.jpg"

        @pytest.fixture
        def mock_select_rotate_image(self, mocker) -> Mock:
            return mocker.patch("robotoff.insights.annotate.select_rotate_image")

        @pytest.fixture
        def nutrient_extraction_insight(self):
            return ProductInsightFactory(
                type="nutrient_extraction", source_image=self.SOURCE_IMAGE
            )

        def test_select_nutrition_image_no_image_id(
            self,
            mock_select_rotate_image: Mock,
            nutrient_extraction_insight: ProductInsightFactory,
        ):
            product: JSONType = {"images": {}, "lang": "fr"}
            NutrientExtractionAnnotator.select_nutrition_image(
                insight=nutrient_extraction_insight,
                product=product,
            )
            mock_select_rotate_image.assert_not_called()

        def test_select_nutrition_image_no_image_meta(
            self,
            mock_select_rotate_image: Mock,
            nutrient_extraction_insight: ProductInsightFactory,
        ):
            product: JSONType = {"images": {"2": {}}, "lang": "fr"}
            NutrientExtractionAnnotator.select_nutrition_image(
                insight=nutrient_extraction_insight,
                product=product,
            )
            mock_select_rotate_image.assert_not_called()

        def test_select_nutrition_image_already_selected(
            self,
            mock_select_rotate_image: Mock,
            nutrient_extraction_insight: ProductInsightFactory,
        ):
            product: JSONType = {
                "images": {
                    "2": {"sizes": {"full": {"w": 1000, "h": 2000}}},
                    "nutrition_fr": {"imgid": "2"},
                },
                "lang": "fr",
            }
            NutrientExtractionAnnotator.select_nutrition_image(
                insight=nutrient_extraction_insight,
                product=product,
            )
            mock_select_rotate_image.assert_not_called()

        def test_select_nutrition_image(
            self,
            mock_select_rotate_image: Mock,
            nutrient_extraction_insight: ProductInsightFactory,
        ):
            product = {
                "images": {"2": {"sizes": {"full": {"w": 1000, "h": 2000}}}},
                "lang": "fr",
            }
            NutrientExtractionAnnotator.select_nutrition_image(
                insight=nutrient_extraction_insight,
                product=product,
            )
            mock_select_rotate_image.assert_called_once_with(
                product_id=nutrient_extraction_insight.get_product_id(),
                image_id="2",
                image_key="nutrition_fr",
                rotate=None,
                crop_bounding_box=None,
                auth=None,
                is_vote=False,
                insight_id=nutrient_extraction_insight.id,
            )

        def test_select_nutrition_image_override_nutrition_image(
            self,
            mock_select_rotate_image: Mock,
            nutrient_extraction_insight: ProductInsightFactory,
        ):
            product = {
                "images": {
                    "2": {"sizes": {"full": {"w": 1000, "h": 2000}}},
                    # image 1 already selected, should be overridden
                    "nutrition_fr": {"imgid": "1"},
                },
                "lang": "fr",
            }
            NutrientExtractionAnnotator.select_nutrition_image(
                insight=nutrient_extraction_insight,
                product=product,
            )
            mock_select_rotate_image.assert_called_once_with(
                product_id=nutrient_extraction_insight.get_product_id(),
                image_id="2",
                image_key="nutrition_fr",
                rotate=None,
                crop_bounding_box=None,
                auth=None,
                is_vote=False,
                insight_id=nutrient_extraction_insight.id,
            )

        def test_select_nutrition_image_with_rotation_and_nutrition_table_detection(
            self,
            mock_select_rotate_image: Mock,
            nutrient_extraction_insight: ProductInsightFactory,
        ):
            product = {
                "images": {"2": {"sizes": {"full": {"w": 1000, "h": 2000}}}},
                "lang": "fr",
            }
            rotation_data = {"rotation": 90}
            PredictionFactory(
                type=PredictionType.image_orientation,
                data=rotation_data,
                source_image=self.SOURCE_IMAGE,
            )
            image_model = ImageModelFactory(source_image=self.SOURCE_IMAGE)
            detection_data = {
                "objects": [
                    {
                        "label": "nutrition-table",
                        "score": 0.550762104988098,
                        "bounding_box": [
                            0.06199073791503906,
                            0.20298996567726135,
                            0.4177824556827545,
                            0.9909706115722656,
                        ],
                    },
                ]
            }
            ImagePredictionFactory(
                model_name=ObjectDetectionModel.nutrition_table.name,
                data=detection_data,
                image=image_model,
            )
            NutrientExtractionAnnotator.select_nutrition_image(
                insight=nutrient_extraction_insight,
                product=product,
            )
            mock_select_rotate_image.assert_called_once_with(
                product_id=nutrient_extraction_insight.get_product_id(),
                image_id="2",
                image_key="nutrition_fr",
                rotate=rotation_data["rotation"],
                crop_bounding_box=(
                    202.98996567726135,
                    1164.435088634491,
                    990.9706115722656,
                    1876.0185241699219,
                ),
                auth=None,
                is_vote=False,
                insight_id=nutrient_extraction_insight.id,
            )
