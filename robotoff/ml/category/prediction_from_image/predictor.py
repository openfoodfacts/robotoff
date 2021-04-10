import joblib
import numpy as np
from robotoff.ml.category.prediction_from_image.helpers import list_categories
from robotoff.ml.category.prediction_from_image.cleaner import Cleaner
#from robotoff.ml.category.prediction_from_image.ocr import get_data_from_ocr, get_data_from_url


class Predictor():

    model = None

    def __init__(self, text):
        self.text = text


    def load_model(self):
        if Predictor.model is None:
            """change the path whith your model name and location.
            The first time you use the model, load it from Le Wagon GD file with
            loader.py"""
            Predictor.model = joblib.load('bestridge.joblib')
            #https://drive.google.com/file/d/1XaIUqGmTmy70XQ9DETL2Halbj_1yP6d_/view?usp=sharing
        self.model = Predictor.model

    def preprocess(self):
        cleaner = Cleaner()
        text = cleaner.clean_ocr_text(text=self.text, spellcheck=None)
        return text

    def predict(self):
        """ This function returns the prediction for a given OCR. If > thresold, it
        returns directly the category. If not, the model returns the two categories
        between which it hesitates"""
        d = self.model.decision_function([self.text])
        probabilities = [np.exp(x) / np.sum(np.exp(d)) for x in d]
        proba = list(probabilities[0])
        return proba


if __name__ == '__main__':

    predictor = Predictor(text=Predictor.text)
    predictor.load_model()
    predictor.preprocess()
    print(predictor.predict())
