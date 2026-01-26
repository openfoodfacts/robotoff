
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
    
    predictions: list[list[LanguagePrediction]] = []
    r = http_session.post(
    f"{settings.FASTTEXT_SERVER_URI}/predict?k={k}&threshold={threshold}",
    json=texts,
    timeout=5,
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


PORTUGUESE_NUTRITION_KEYWORDS = (
    "valor energético",
    "energia",
    "gorduras",
    "hidratos",
    "carboidratos",
    "proteínas",
    "sal",
    "porção",
    "porcao",
)

def looks_like_portuguese_nutrition(text: str) -> bool:
    text = text.lower()
    return any(keyword in text for keyword in PORTUGUESE_NUTRITION_KEYWORDS)



def predict_lang(
    text: str, k: int = 10, threshold: float = 0.0
) -> list[LanguagePrediction]:
    predictions = predict_lang_batch([text], k, threshold)[0]

    if (
        predictions
        and predictions[0].lang == "es"
        and looks_like_portuguese_nutrition(text)
    ):
        predictions[0] = LanguagePrediction(
            lang="pt",
            confidence=predictions[0].confidence,
        )

    
    return predictions
