import pytest

from robotoff.insights.importer import (
    ImageOrientationImporter,
    NutritionImageImporter,
    import_product_predictions,
)
from robotoff.models import Prediction as PredictionModel
from robotoff.types import (
    InsightType,
    Prediction,
    PredictionType,
    ProductIdentifier,
    ServerType,
)

from ..models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    PredictionFactory,
    clean_db,
)

DEFAULT_BARCODE = "1234567891234"


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        # clean db
        clean_db()
        # Run the test case.
        yield
        clean_db()


class TestNutritionImageImporter:
    @classmethod
    def generate_image_prediction(
        cls,
        image,
        objects,
        default_label="nutrition-table",
        default_score=0.8,
        default_bounding_box=(0.1, 0.1, 0.4, 0.4),
    ):
        max_confidence = None
        for obj in objects:
            if "label" not in obj:
                obj["label"] = default_label
            if "score" not in obj:
                obj["score"] = default_score
            if "bounding_box" not in obj:
                obj["bounding_box"] = default_bounding_box

            if max_confidence is None or obj["score"] >= max_confidence:
                max_confidence = obj["score"]

        return ImagePredictionFactory(
            image=image,
            data={"objects": objects},
            model_name="nutrition_table",
            model_version="yolo-nutrition-table-1.0",
            max_confidence=max_confidence,
        )

    def test_get_nutrition_table_predictions(self):
        image_1 = ImageModelFactory(server_type=ServerType.off.name)
        image_2 = ImageModelFactory(server_type=ServerType.off.name)
        image_3 = ImageModelFactory(server_type=ServerType.obf.name)

        self.generate_image_prediction(
            image_1,
            [
                {},
                {"label": "nutrition-table-small"},
                {"score": 0.1, "bounding_box": (0.0, 0.0, 0.3, 0.3)},
            ],
        )
        self.generate_image_prediction(image_2, [{}, {}])
        self.generate_image_prediction(image_3, [{}])

        assert NutritionImageImporter.get_nutrition_table_predictions(
            ProductIdentifier(barcode=image_1.barcode, server_type=ServerType.off),
            min_score=0.5,
        ) == {
            image_1.source_image: [
                {
                    "bounding_box": [0.1, 0.1, 0.4, 0.4],
                    "label": "nutrition-table",
                    "score": 0.8,
                }
            ]
        }

        assert NutritionImageImporter.get_nutrition_table_predictions(
            ProductIdentifier(barcode=image_1.barcode, server_type=ServerType.off),
            min_score=0.05,
        ) == {
            image_1.source_image: [
                {
                    "bounding_box": [0.1, 0.1, 0.4, 0.4],
                    "label": "nutrition-table",
                    "score": 0.8,
                },
                {
                    "bounding_box": [0.0, 0.0, 0.3, 0.3],
                    "label": "nutrition-table",
                    "score": 0.1,
                },
            ]
        }


class TestImageOrientationImporter:
    def test_generate_candidates_right_orientation(self, mocker):
        prediction_data = {
            "orientation": "right",
            "rotation": 270,
            "count": {"up": 4, "right": 96},
        }

        prediction = Prediction(
            barcode="1234567890123",
            type=PredictionType.image_orientation,
            source_image="/123/456/789/1234/1.jpg",
            server_type=ServerType.off,
            data=prediction_data,
            value_tag=None,
        )

        # Generate candidates
        candidates = list(
            ImageOrientationImporter.generate_candidates(
                product=None,
                predictions=[prediction],
                product_id=ProductIdentifier("1234567890123", ServerType.off),
            )
        )

        # Check we have one candidate
        assert len(candidates) == 1
        candidate = candidates[0]

        # Check candidate properties
        assert candidate.type == InsightType.image_orientation.name
        assert candidate.barcode == "1234567890123"
        assert candidate.source_image == "/123/456/789/1234/1.jpg"
        assert candidate.data["rotation"] == 270
        assert candidate.data["orientation"] == "right"
        assert candidate.data["orientation_fraction"] == 96 / 100
        assert candidate.automatic_processing is True

    def test_no_candidates_for_upright_image(self, mocker):
        prediction_data = {
            "orientation": "up",
            "rotation": 0,
            "count": {"up": 96, "right": 4},
        }

        prediction = Prediction(
            barcode="1234567890123",
            type=PredictionType.image_orientation,
            source_image="/123/456/789/1234/1.jpg",
            server_type=ServerType.off,
            data=prediction_data,
            value_tag=None,
        )

        candidates = list(
            ImageOrientationImporter.generate_candidates(
                product=None,
                predictions=[prediction],
                product_id=ProductIdentifier("1234567890123", ServerType.off),
            )
        )

        assert len(candidates) == 0

    def test_no_candidates_for_low_confidence(self, mocker):
        prediction_data = {
            "orientation": "right",
            "rotation": 270,
            "count": {"up": 20, "right": 80},  # only 80% confidence, below threshold
        }

        prediction = Prediction(
            barcode="1234567890123",
            type=PredictionType.image_orientation,
            source_image="/123/456/789/1234/1.jpg",
            server_type=ServerType.off,
            data=prediction_data,
            value_tag=None,
        )

        candidates = list(
            ImageOrientationImporter.generate_candidates(
                product=None,
                predictions=[prediction],
                product_id=ProductIdentifier("1234567890123", ServerType.off),
            )
        )

        assert len(candidates) == 0


def test_import_product_predictions():
    new_predictor_version = "2"
    old_predictor_version = None
    source_image_1 = "/123/456/789/1234/1.jpg"
    source_image_2 = "/123/456/789/1234/2.jpg"
    value_tag = "en:organic"
    prediction_1 = PredictionFactory(
        barcode=DEFAULT_BARCODE,
        type=PredictionType.label.name,
        source_image=source_image_1,
        predictor_version=old_predictor_version,
        value_tag=value_tag,
    )
    prediction_2 = PredictionFactory(
        barcode=DEFAULT_BARCODE,
        type=PredictionType.label.name,
        source_image=source_image_2,
        predictor_version=old_predictor_version,
        value_tag=value_tag,
    )
    prediction_3 = PredictionFactory(
        barcode=DEFAULT_BARCODE,
        type=PredictionType.label.name,
        source_image=source_image_1,
        server_type=ServerType.obf.name,
        predictor_version=old_predictor_version,
        value_tag=value_tag,
    )
    prediction_4 = PredictionFactory(
        barcode=DEFAULT_BARCODE,
        type=PredictionType.label.name,
        source_image=source_image_1,
        predictor_version=old_predictor_version,
        value_tag="en:fairtrade-international",
    )
    prediction_5 = PredictionFactory(
        barcode=DEFAULT_BARCODE,
        type=PredictionType.store.name,
        source_image=source_image_1,
        predictor_version=old_predictor_version,
        value_tag="Auchan",
    )
    product_predictions = [
        Prediction(
            barcode=DEFAULT_BARCODE,
            type=PredictionType.label,
            source_image=source_image_1,
            server_type=ServerType.off,
            predictor_version=new_predictor_version,
            value_tag=value_tag,
        ),
    ]
    imported, deleted = import_product_predictions(
        DEFAULT_BARCODE,
        ServerType.off,
        product_predictions,
        delete_previous_versions=True,
    )
    assert PredictionModel.get_or_none(id=prediction_1.id) is None
    assert PredictionModel.get_or_none(id=prediction_2.id) is not None
    assert PredictionModel.get_or_none(id=prediction_3.id) is not None
    # Prediction with same image, type, server type, barcode and with old
    # version gets deleted
    assert PredictionModel.get_or_none(id=prediction_4.id) is None
    # Prediction with same image, server type, barcode, with old
    # version but with different type does *NOT* get deleted
    assert PredictionModel.get_or_none(id=prediction_5.id) is not None
    insights = list(
        PredictionModel.select().where(
            PredictionModel.barcode == DEFAULT_BARCODE,
            PredictionModel.server_type == "off",
            PredictionModel.value_tag == value_tag,
            PredictionModel.type == PredictionType.label.name,
            PredictionModel.source_image == source_image_1,
        )
    )
    assert len(insights) == 1
    assert insights[0].id not in (prediction_1.id, prediction_2.id, prediction_3.id)
    assert imported == 1
    assert deleted == 2
