from typing import Any, Dict

ADD_LOGO_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Add Logo",
    "type": "object",
    "properties": {
        "logos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "bounding_box": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {"type": "number"},
                    },
                },
                "required": ["id", "bounding_box"],
            },
        },
        "image_url": {"type": "string", "format": "uri"},
    },
    "required": ["image_url", "logos"],
}
