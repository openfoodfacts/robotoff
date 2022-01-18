import dataclasses
import itertools
from enum import Enum, unique
from typing import Any, Dict, Iterable, List, Optional

import dacite


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
    data: Dict[str, Any]
    value_tag: Optional[str] = None
    value: Optional[str] = None
    automatic_processing: Optional[bool] = None
    predictor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self, dict_factory=dict_factory)


def dict_factory(*args, **kwargs):
    d = dict(*args, **kwargs)
    for key, value in d.items():
        if isinstance(value, PredictionType):
            d[key] = value.name

    return d


@dataclasses.dataclass
class ProductPredictions:
    predictions: List[Prediction]
    barcode: str
    type: PredictionType
    source_image: Optional[str] = None

    @classmethod
    def merge(cls, items: Iterable["ProductPredictions"]) -> "ProductPredictions":
        items = list(items)
        if len(items) == 0:
            raise ValueError("no items to merge")

        elif len(items) == 1:
            return items[0]

        for field_name in ("type", "barcode", "source_image"):
            values = set(getattr(x, field_name) for x in items)
            if len(values) > 1:
                raise ValueError(
                    "more than one value for '{}': {}".format(field_name, values)
                )
        item = items[0]
        predictions = list(
            itertools.chain.from_iterable((item.predictions for item in items))
        )
        return cls(
            predictions=predictions,
            barcode=item.barcode,
            type=item.type,
            source_image=item.source_image,
        )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self, dict_factory=dict_factory)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductPredictions":
        return dacite.from_dict(
            data_class=cls, data=data, config=dacite.Config(cast=[PredictionType])
        )
