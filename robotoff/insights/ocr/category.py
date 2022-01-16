from typing import List, Union

import numpy as np

from robotoff.insights import InsightType
from robotoff.insights.dataclass import RawInsight
from robotoff.insights.ocr.dataclass import OCRResult, get_text
from robotoff.prediction.category.prediction_from_ocr.constants import LIST_CATEGORIES
from robotoff.prediction.category.prediction_from_ocr.predictor import Predictor

HESITATION_THRESHOLD = 0.012


def predict_ocr_categories(content: Union[OCRResult, str]) -> List[RawInsight]:
    """Run prediction on a given OCR and return insights.

    If the model hesitates between 2 categories, both are returned as insights.
    Otherwise, only 1 category is returned. We consider the model to be
    "hesitating" if the probability of the top 2 categories are separated by
    less than `HESITATION_THRESHOLD` percent.
    """
    text = get_text(content)
    if not text:
        return []

    probabilities = Predictor(text=text).run()
    indices_max = np.argsort(probabilities)

    # Select top 2 categories
    best_index = indices_max[-1]
    best_proba = probabilities[best_index]

    second_index = indices_max[-2]
    second_proba = probabilities[second_index]

    # Return either top category only or both, depending on the gap
    results = [_get_raw_insight(best_proba, best_index)]
    if (best_proba - second_proba) <= HESITATION_THRESHOLD:
        results.append(_get_raw_insight(second_proba, second_index))
    return results


def _get_raw_insight(probabilily: float, index: int) -> RawInsight:
    return RawInsight(
        type=InsightType.category,
        value_tag=LIST_CATEGORIES[index],
        data={"confidence": round(probabilily, 4),},
        predictor="ridge_model-ml",
    )
