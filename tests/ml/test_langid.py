import pytest

from robotoff.ml.langid import (
    DEFAULT_LANGUAGE_IDENTIFIER,
    LanguageIdentifier,
    LanguagePrediction,
)


@pytest.mark.parametrize(
    "text,lang",
    [
        ("farine de blé", "fr"),
        ("black Lentils, water", "en"),
        ("cukor, kakaóvaj, teljes tejpor, mogyoró (12%)", "hu"),
    ],
)
def test_langid_identify(text: str, lang: str):
    identifier: LanguageIdentifier = DEFAULT_LANGUAGE_IDENTIFIER.get()
    predictions = identifier.predict(text)
    assert isinstance(predictions, list)
    assert all((isinstance(x, LanguagePrediction) for x in predictions))

    assert len(predictions) > 0
    print(predictions)
    first_prediction = predictions[0]
    assert first_prediction.lang == lang
