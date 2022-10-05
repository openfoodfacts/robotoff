import dataclasses
import datetime
from enum import Enum, unique
from typing import Any, Dict, Optional


@unique
class PredictionType(str, Enum):
    """PredictionType defines the type of the prediction."""

    ingredient_spellcheck = "ingredient_spellcheck"
    packager_code = "packager_code"
    label = "label"
    category = "category"
    image_flag = "image_flag"
    product_weight = "product_weight"
    expiration_date = "expiration_date"
    brand = "brand"
    image_orientation = "image_orientation"
    store = "store"
    nutrient = "nutrient"
    trace = "trace"
    packaging = "packaging"
    location = "location"
    nutrient_mention = "nutrient_mention"
    image_lang = "image_lang"
    nutrition_image = "nutrition_image"
    nutrition_table_structure = "nutrition_table_structure"


@dataclasses.dataclass
class Prediction:
    type: PredictionType
    data: Dict[str, Any] = dataclasses.field(default_factory=dict)
    value_tag: Optional[str] = None
    value: Optional[str] = None
    automatic_processing: Optional[bool] = None
    predictor: Optional[str] = None
    barcode: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    source_image: Optional[str] = None
    server_domain: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self, dict_factory=dict_factory)


def dict_factory(*args, **kwargs):
    d = dict(*args, **kwargs)
    for key, value in d.items():
        if isinstance(value, PredictionType):
            d[key] = value.name

    return d
