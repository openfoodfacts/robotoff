import pytest

from robotoff.insights.importer import NutritionImageImporter
from robotoff.types import ProductIdentifier, ServerType

from ..models_utils import ImageModelFactory, ImagePredictionFactory, clean_db


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        # clean db
        clean_db()
        # Run the test case.
        yield
        clean_db()


def generate_image_prediction(
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
        model_name="nutrition-table",
        model_version="tf-nutrition-table-1.0",
        max_confidence=max_confidence,
    )


def test_get_nutrition_table_predictions():
    image_1 = ImageModelFactory(server_type=ServerType.off.name)
    image_2 = ImageModelFactory(server_type=ServerType.off.name)
    image_3 = ImageModelFactory(server_type=ServerType.obf.name)

    generate_image_prediction(
        image_1,
        [
            {},
            {"label": "nutrition-table-small"},
            {"score": 0.1, "bounding_box": (0.0, 0.0, 0.3, 0.3)},
        ],
    )
    generate_image_prediction(image_2, [{}, {}])
    generate_image_prediction(image_3, [{}])

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
