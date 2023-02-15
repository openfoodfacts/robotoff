from robotoff.types import JSONType, NeuralCategoryClassifierModel

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
                    "server_domain": {"type": "string"},
                    "barcode": {"type": "string"},
                    "image_id": {"type": "string"},
                    "model_name": {"type": "string"},
                    "model_version": {"type": "string"},
                    "data": {"type": "object"},
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
                "predictors": {
                    "type": "array",
                    "items": {"enum": ["neural", "matcher"]},
                },
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
                },
                "deepest_only": {
                    "type": "boolean",
                },
                "threshold": {"type": "number"},
                "predictors": {
                    "type": "array",
                    "items": {"enum": ["neural", "matcher"]},
                },
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
    },
    "required": ["annotations"],
}
