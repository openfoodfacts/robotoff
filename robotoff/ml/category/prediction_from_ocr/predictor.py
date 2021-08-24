import typing

import joblib
import numpy as np
from scipy.special import softmax
from sklearn.pipeline import Pipeline

from .cleaner import clean_ocr_text
from .constants import RIDGE_PREDICTOR_FILEPATH


class Predictor:
    """Wrap the ML model that predicts categories from an OCR text."""

    model: typing.Optional[Pipeline] = None

    def __init__(self, text: str):
        self.text = text

    def run(self) -> np.ndarray:
        """Run predictor on the given text."""
        self._load_model()
        self._preprocess()
        return self._predict()

    def _load_model(self) -> None:
        """Load model pipeline if not already initialized.

        Change the path with your model name and location.
        The first time you use the model, load it from Le Wagon GD file with
        `loader.py`.

        https://drive.google.com/file/d/1XaIUqGmTmy70XQ9DETL2Halbj_1yP6d_/view?usp=sharing
        """
        if Predictor.model is None:
            Predictor.model = joblib.load(RIDGE_PREDICTOR_FILEPATH)

    def _preprocess(self) -> None:
        """Preprocess input text."""
        self.text = clean_ocr_text(text=self.text)

    def _predict(self) -> np.ndarray:
        """Return the predictions for a given OCR text as an array of probabilities."""
        if self.model is None:
            raise Exception("Model must be loaded first !")

        return softmax(
            self.model.decision_function(
                [self.text],
            )
        )[0]
