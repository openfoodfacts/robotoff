
import joblib
import numpy as np
from robotoff.ml.category.prediction_from_ocr.helpers import list_categories
from robotoff.ml.category.prediction_from_ocr.predictor import Predictor
from robotoff.ml.category.prediction_from_ocr.cleaner import clean_ocr_text
from typing import Dict, List, Optional, Union
from robotoff.insights.ocr.dataclass import OCRResult, get_text
from robotoff.insights import InsightType
from robotoff.insights.dataclass import RawInsight


def _get_raw_insight(probabilities:np.ndarray, index:int)->RawInsight:
    return RawInsight(
        type=InsightType.category,
        value_tag= list_categories[index],
        data={
            "proba": list_categories[index],
            "max_confidence": round(probabilities[index], 4),
        },
        predictor="ridge_model-ml",
    )


def find_category(content: Union[OCRResult, str])-> List[RawInsight]:
    """ This function returns the prediction for a given OCR. If > thresold, it
        returns directly the category. If not, the model returns the two categories
        between which it hesitates"""

    text = get_text(content)
    if not text:
        return []

    results: List[RawInsight] = []

    predictor = Predictor(text=text)
    predictor.load_model()
    predictor.preprocess()
    proba = predictor.predict()
    threshold=0.012
    list_cat = list_categories

    indices_max = np.argsort([-x for x in proba])
    if (proba[indices_max[0]] - proba[indices_max[1]]) > threshold:
        results.append(_get_raw_insight(proba, indices_max[0]))
    else:
        results.append(_get_raw_insight(proba, indices_max[0]))
        results.append(_get_raw_insight(proba, indices_max[1]))
    return results


