import pytest

from robotoff.insights.importer import (
    ImageOrientationImporter,
    NutritionImageImporter,
    import_product_predictions,
)
from robotoff.models import Prediction as PredictionModel
from robotoff.products import Product
from robotoff.types import Prediction, PredictionType, ProductIdentifier, ServerType

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
    @pytest.fixture
    def image_model_factory(self):
        def _factory(barcode="1234567890123", image_id="1", server_type=ServerType.off):
            return ImageModelFactory(
                barcode=barcode,
                image_id=image_id,
                server_type=server_type,
                source_image=f"/source/image/path/{image_id}.jpg",
            )

        return _factory

    @pytest.fixture
    def prediction_factory(self):
        def _factory(
            barcode="1234567890123",
            source_image="/source/image/path/1.jpg",
            orientation="right",
            rotation=270,
            count=None,
            server_type=ServerType.off,
        ):
            if count is None:
                count = {"up": 1, "right": 19}

            return PredictionFactory(
                type=PredictionType.image_orientation,
                barcode=barcode,
                source_image=source_image,
                data={
                    "orientation": orientation,
                    "rotation": rotation,
                    "count": count,
                },
                server_type=server_type,
            )

        return _factory

    def test_import_image_orientation_prediction(self, prediction_factory, peewee_db):
        factory_prediction = prediction_factory()

        # Get the data from the factory prediction
        pred_data = {
            "barcode": factory_prediction.barcode,
            "server_type": factory_prediction.server_type,
            "type": factory_prediction.type,
            "source_image": factory_prediction.source_image,
            "data": factory_prediction.data,
            "value_tag": factory_prediction.value_tag,
        }

        # Delete the factory-created record from the database
        factory_prediction.delete_instance()

        # Create a new Prediction object that isn't in the database
        prediction = Prediction(**pred_data)

        imported, deleted = import_product_predictions(
            prediction.barcode, prediction.server_type, [prediction]
        )

        assert imported == 1
        assert deleted == 0

        # Verify prediction was stored in database
        db_prediction = PredictionModel.get(
            PredictionModel.barcode == prediction.barcode,
            PredictionModel.type == PredictionType.image_orientation,
        )

        assert db_prediction.data["orientation"] == "right"
        assert db_prediction.data["rotation"] == 270
        assert db_prediction.data["count"]["right"] == 19

    def test_generate_insight_with_confidence(self, prediction_factory, mocker):
        factory_prediction = prediction_factory(
            count={"up": 1, "right": 19}  # 95% confidence for "right"
        )

        factory_prediction.delete_instance()

        prediction_data = {
            "barcode": factory_prediction.barcode,
            "server_type": factory_prediction.server_type,
            "type": factory_prediction.type,
            "source_image": factory_prediction.source_image,
            "data": factory_prediction.data,
            "value_tag": factory_prediction.value_tag,
        }

        prediction = Prediction(**prediction_data)

        # Create a product
        product = Product(
            {
                "code": prediction.barcode,
                "images": {"1": {"imgid": "1"}, "front_it": {"imgid": "1"}},
            }
        )

        # Generate candidates
        product_id = ProductIdentifier(prediction.barcode, prediction.server_type)
        candidates = list(
            ImageOrientationImporter.generate_candidates(
                product,
                [prediction],
                product_id,
            )
        )

        # Verify that one candidate was generated
        assert len(candidates) == 1

        # Verify properties of the candidate
        candidate = candidates[0]
        assert candidate.value == "front_it"
        # Calculate expected confidence
        total = sum(prediction.data["count"].values())
        expected_confidence = prediction.data["count"]["right"] / total

        assert candidate.automatic_processing is False
        assert candidate.confidence == expected_confidence
        assert candidate.data["rotation"] == 270

    def test_image_orientation_settings(self, prediction_factory, mocker):
        factory_prediction = prediction_factory(count={"up": 1, "right": 19})

        pred_data = {
            "barcode": factory_prediction.barcode,
            "server_type": factory_prediction.server_type,
            "type": factory_prediction.type,
            "source_image": factory_prediction.source_image,
            "data": factory_prediction.data,
            "value_tag": factory_prediction.value_tag,
        }

        factory_prediction.delete_instance()

        prediction = Prediction(**pred_data)

        product = Product(
            {
                "code": prediction.barcode,
                "images": {
                    "1": {"imgid": "1"},
                    "2": {"imgid": "2"},
                    "nutrition_fr": {"imgid": "1"},
                    "front_it": {"imgid": "1"},
                    "front_en": {"imgid": "2"},
                },
            }
        )
        candidates = list(
            ImageOrientationImporter.generate_candidates(
                product,
                [prediction],
                ProductIdentifier(
                    barcode=prediction.barcode, server_type=prediction.server_type
                ),
            )
        )

        assert len(candidates) == 2
        assert candidates[0].value == "nutrition_fr"
        assert candidates[0].automatic_processing is False
        # Verify confidence is set correctly (right / total words)
        expected_confidence = 19 / 20
        assert candidates[0].confidence == expected_confidence

        assert candidates[1].value == "front_it"


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
