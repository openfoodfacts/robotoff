import joblib
import numpy as np
from scipy import special
from scipy.special import softmax
from robotoff.ml.category.prediction_from_ocr.helpers import list_categories
from robotoff.ml.category.prediction_from_ocr.cleaner import clean_ocr_text



class Predictor():

    model = None

    def __init__(self, text):
        self.text = text


    def load_model(self)-> None:
        if Predictor.model is None:
            """change the path whith your model name and location.
            The first time you use the model, load it from Le Wagon GD file with
            loader.py"""
            Predictor.model = joblib.load('bestridge.joblib')
            #https://drive.google.com/file/d/1XaIUqGmTmy70XQ9DETL2Halbj_1yP6d_/view?usp=sharing
        self.model = Predictor.model

    def preprocess(self)-> str:
        text = clean_ocr_text(text=self.text)
        return text

    def predict(self)->str:
        """ This function returns the prediction for a given OCR. If > thresold, it
        returns directly the category. If not, the model returns the two categories
        between which it hesitates"""
        d = self.model.decision_function([self.text])
        #probabilities = [np.exp(x) / np.sum(np.exp(d)) for x in d]
        probabilities = softmax(d)
        proba = list(probabilities[0])
        return proba


