from typing import Annotated

from pydantic import BaseModel, Field

from robotoff.types import JSONType, NeuralCategoryClassifierModel, ServerType

IMAGE_PREDICTION_IMPORTER_SCHEMA: JSONType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Image Prediction Importer",
    "type": "object",
    "properties": {
        "predictions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "barcode": {"type": "string"},
                    "image_id": {"type": "string"},
                    "model_name": {"type": "string"},
                    "model_version": {"type": "string"},
                    "data": {"type": "object"},
                    "server_type": {"type": "string"},
                },
                "required": [
                    "barcode",
                    "image_id",
                    "model_name",
                    "model_version",
                    "data",
                ],
            },
        }
    },
    "required": ["predictions"],
}

UPDATE_LOGO_SCHEMA: JSONType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Update Logo",
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
        "type": {"type": "string", "minLength": 1},
    },
    "required": ["type"],
}

PREDICT_CATEGORY_SCHEMA: JSONType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Predict Category",
    "anyOf": [
        {
            "type": "object",
            "properties": {
                "barcode": {
                    "type": "string",
                    "minLength": 1,
                },
                "deepest_only": {
                    "type": "boolean",
                },
                "threshold": {"type": "number"},
                "neural_model_name": {
                    "type": "string",
                    "enum": [x.name for x in NeuralCategoryClassifierModel],
                },
            },
            "required": ["barcode"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "product": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": "string",
                            "minLength": 1,
                        },
                        "ingredients_tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "ocr": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "image_embeddings": {
                            "type": "array",
                            "maxItems": 10,
                            "items": {
                                "type": "array",
                                "minItems": 512,
                                "maxItems": 512,
                                "items": {"type": "number"},
                            },
                        },
                        "nutriments": {
                            "type": "object",
                            "properties": {
                                "fat_100g": {"type": "number"},
                                "saturated-fat_100g": {"type": "number"},
                                "carbohydrates_100g": {"type": "number"},
                                "sugars_100g": {"type": "number"},
                                "fiber_100g": {"type": "number"},
                                "proteins_100g": {"type": "number"},
                                "salt_100g": {"type": "number"},
                                "energy-kcal_100g": {"type": "number"},
                                "fruits-vegetables-nuts_100g": {"type": "number"},
                            },
                            "additionalProperties": False,
                        },
                    },
                    "required": [],
                    "additionalProperties": False,
                    "minProperties": 1,
                },
                "deepest_only": {
                    "type": "boolean",
                },
                "threshold": {"type": "number"},
                "lang": {
                    "type": "string",
                    "minLength": 1,
                },
                "neural_model_name": {
                    "type": "string",
                    "enum": [x.name for x in NeuralCategoryClassifierModel],
                },
            },
            "required": ["product"],
            "additionalProperties": False,
        },
    ],
}


ANNOTATE_LOGO_SCHEMA: JSONType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Annotate Logo",
    "type": "object",
    "properties": {
        "annotations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": ["string", "null"],
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "brand",
                            "category",
                            "label",
                            "no_logo",
                            "nutritional_label",
                            "packager_code",
                            "packaging",
                            "qr_code",
                            "store",
                        ],
                    },
                    "logo_id": {"type": "integer"},
                },
                "required": ["value", "type", "logo_id"],
            },
        },
        "server_type": {
            "type": "string",
            "enum": [server_type.name for server_type in ServerType],
            "default": ServerType.off,
        },
    },
    "required": ["annotations"],
}


class LanguagePredictorResourceParams(BaseModel):
    text: Annotated[
        str, Field(..., description="the text to predict language of", min_length=1)
    ]
    k: Annotated[
        int, Field(default=10, description="the number of predictions to return", ge=1)
    ]
    threshold: Annotated[
        float,
        Field(default=0.01, description="the minimum confidence threshold", ge=0, le=1),
    ]
