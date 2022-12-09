import abc
import dataclasses

from langid import langid

from robotoff.utils.cache import CachedStore


@dataclasses.dataclass
class LanguagePrediction:
    lang: str
    confidence: float


class LanguageIdentifier(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def predict(
        self, text: str, k: int = 10, threshold: float = 0.0
    ) -> list[LanguagePrediction]:
        pass


class LangidLanguageIdentifier(LanguageIdentifier):
    def __init__(self, model):
        self.model = model

    @classmethod
    def load(cls):
        model = langid.LanguageIdentifier.from_modelstring(
            langid.model, norm_probs=True
        )
        return cls(model)

    def predict(
        self, text: str, k: int = 10, threshold: float = 0.0
    ) -> list[LanguagePrediction]:
        predictions: list[LanguagePrediction] = []
        rank = self.model.rank(text)

        added: int = 0
        for language, confidence in rank:
            if confidence >= threshold:
                prediction = LanguagePrediction(language, confidence)
                predictions.append(prediction)
                added += 1
            else:
                break

            if added >= k:
                break

        return predictions


class FastTextLanguageIdentifier(LanguageIdentifier):
    def __init__(self, model):
        self.model = model

    def predict(
        self, text: str, k: int = 10, threshold: float = 0.0
    ) -> list[LanguagePrediction]:
        predictions: list[LanguagePrediction] = []
        languages, confidences = self.model.predict(text, k=k, threshold=threshold)

        for language, confidence in zip(languages, confidences):
            # language str format is __label__en
            language = language[9:]
            prediction = LanguagePrediction(language, confidence)
            predictions.append(prediction)

        return predictions


DEFAULT_LANGUAGE_IDENTIFIER = CachedStore(LangidLanguageIdentifier.load)
