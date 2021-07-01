import typing

import typing_extensions


class XGFoodPrediction(typing_extensions.TypedDict):
    prediction_G1: str
    confidence_G1: float

    prediction_G2: str
    confidence_G2: float


class IngredientDetailed(typing_extensions.TypedDict, total=False):
    percent_estimate: float
    percent_max: float
    percent_min: float
    text: str


IngredientDetailedList_T = typing.List[IngredientDetailed]
PreprocessedX_T = typing.Dict[str, float]
