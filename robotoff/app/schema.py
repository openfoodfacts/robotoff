from typing import Any, Dict

IMAGE_PREDICTION_IMPORTER_SCHEMA: Dict[str, Any] = {
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

UPDATE_LOGO_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Update Logo",
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
        "type": {"type": "string", "minLength": 1},
    },
    "required": ["value", "type"],
}
