
import joblib
import numpy as np
from robotoff.ml.category.prediction_from_image.helpers import list_categories
from robotoff.ml.category.prediction_from_image.predictor import Predictor
from robotoff.ml.category.prediction_from_image.cleaner import Cleaner
from typing import Dict, List, Optional, Union
from robotoff.insights.ocr.dataclass import OCRResult, get_text
from robotoff.insights import InsightType
from robotoff.insights.dataclass import RawInsight


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
        results.append(
                RawInsight(
                    type=InsightType.category,
                    data={"proba": list_cat[indices_max[0]], "max_confidence": round(proba[indices_max[0]], 4)},
                    predictor="ridge_model-ml"
                )
            )
    else:
        results.append(
                RawInsight(
                    type=InsightType.category,
                    data={"data1": list_cat[indices_max[0]], "max_confidence_1": round(proba[indices_max[0]], 4), "data2":list_cat[indices_max[1]], "max_confidence_2": round(proba[indices_max[1]], 4)},
                    predictor="ridge_model-ml",
                )
            )
    return results

if __name__ == '__main__':
    print(find_category())
