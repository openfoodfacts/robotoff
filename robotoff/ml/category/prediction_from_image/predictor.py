import joblib
import numpy as np
from robotoff.ml.category.prediction_from_image.helpers import list_categories
from robotoff.ml.category.prediction_from_image.cleaner import Cleaner
from robotoff.ml.category.prediction_from_image.ocr import get_data_from_ocr, get_data_from_url


class Predictor():

    model = None

    """ get text from url"""
    #url= 'https://static.openfoodfacts.org/images/products/00390804/1.jpg'
    #text = get_data_from_url(url)

    """ get text from json OCR """
    url= 'https://static.openfoodfacts.org/images/products/00390804/1.json'
    text = get_data_from_ocr(url)


    """ applies the same preprocessing as the model (but with a different class because it is a string and not a
     dataframe)"""
    cleaner = Cleaner()
    text = cleaner.clean_ocr_text(text=text, spellcheck=None)


    def __init__(self, text):
        self.text = text


    def load_model(self):
        if Predictor.model is None:
            # change the path whith your model name and location
            Predictor.model = joblib.load('bestridge.joblib')
            #https://drive.google.com/file/d/1XaIUqGmTmy70XQ9DETL2Halbj_1yP6d_/view?usp=sharing
        self.model = Predictor.model


    def predict(self, threshold=0.012):
        """ This function returns the prediction for a given OCR. If > thresold, it
        returns directly the category. If not, the model returns the two categories
        between which it hesitates"""
        list_cat = list_categories
        barcode = ''.join(filter(lambda i: i.isdigit(), self.url))[:-1]
        d = self.model.decision_function([self.text])
        probabilities = [np.exp(x) / np.sum(np.exp(d)) for x in d]
        proba = list(probabilities[0])
        indices_max = np.argsort([-x for x in proba])

        if (proba[indices_max[0]] - proba[indices_max[1]]) > threshold:
            return {"barcode": barcode,
                    "data": list_cat[indices_max[0]],
                    "max_confidence": round(proba[indices_max[0]], 4)
                    }
        else:
             return {"barcode": barcode,
                    "data_1": list_cat[indices_max[0]],
                     "max_confidence_1": round(proba[indices_max[0]], 4),
                     "data_2": list_cat[indices_max[1]],
                    "max_confidence_2": round(proba[indices_max[1]], 4)}




if __name__ == '__main__':

    predictor = Predictor(text=Predictor.text)
    predictor.load_model()
    print(predictor.predict(threshold=0.012))
