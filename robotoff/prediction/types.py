import dataclasses
import datetime
from typing import Any, Optional

from robotoff.types import PredictionType


@dataclasses.dataclass
class Prediction:
    type: PredictionType
    data: dict[str, Any] = dataclasses.field(default_factory=dict)
    value_tag: Optional[str] = None
    value: Optional[str] = None
    automatic_processing: Optional[bool] = None
    predictor: Optional[str] = None
    barcode: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    source_image: Optional[str] = None
    server_domain: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self, dict_factory=dict_factory)


def dict_factory(*args, **kwargs):
    d = dict(*args, **kwargs)
    for key, value in d.items():
        if isinstance(value, PredictionType):
            d[key] = value.name

    return d
