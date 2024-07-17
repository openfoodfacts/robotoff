"""Module to perform language identification (langid).

Under the hood, we use a Rust inference server, serving fasttext lid.176.bin
model. 176 languages are supported.
See https://fasttext.cc/docs/en/language-identification.html for more
information.
"""
import dataclasses

from robotoff import settings
from robotoff.utils import http_session


@dataclasses.dataclass
class LanguagePrediction:
    lang: str
    confidence: float


def predict_lang_batch(
    texts: list[str], k: int = 10, threshold: float = 0.0
) -> list[list[LanguagePrediction]]:
    """Predict the language of a list of texts (batch-mode).

    :param texts: The texts we want to know the language of
    :param k: number of detected language to return per text, defaults to 10
    :param threshold: minimum confidence threshold of predictions, defaults to
        0.0
    :return: a list of list of `LanguagePrediction` (one for each text sample)
        sorted by descending confidence scores
    """
    predictions: list[list[LanguagePrediction]] = []
    r = http_session.post(
        f"{settings.FASTTEXT_SERVER_URI}/predict?k={k}&threshold={threshold}",
        json=texts,
    )
    response = r.json()
    for lang_list, confidence_list in response:
        predictions.append(
            [
                LanguagePrediction(lang, confidence)
                for lang, confidence in zip(lang_list, confidence_list)
            ]
        )
    return predictions


def predict_lang(
    text: str, k: int = 10, threshold: float = 0.0
) -> list[LanguagePrediction]:
    """Predict the language of `text`.

    :param text: The text we want to know the language of
    :param k: number of detected language to return, defaults to 10
    :param threshold: minimum confidence threshold of predictions, defaults to
        0.0
    :return: a list of `LanguagePrediction`, sorted by descending confidence
        scores
    """
    return predict_lang_batch([text], k, threshold)[0]
