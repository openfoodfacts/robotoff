from robotoff.utils.types import JSONType

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
    "required": ["value", "type"],
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
            },
            "required": ["barcode"],
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
                    },
                    "required": ["product_name"],
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
            },
            "required": ["product"],
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
