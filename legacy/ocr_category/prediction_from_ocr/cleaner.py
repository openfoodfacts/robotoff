import re
import string
import unicodedata


def clean_ocr_text(text: str) -> str:
    """Clean an OCR text.

    Cleaning steps:
    - remove punctuation
    - remove non-alphanumeric characters
    - remove spelling mistakes
    - remove accents

    We removed the spellchecker part here because our model don't need it to improve but you can find more details about it on this repo https://github.com/Laurel16/OpenFoodFactsCategorizer/blob/master/OpenFoodFactsCategorizer/cleaner.py)
    """

    clean_functions = [
        _lower,
        _remove_punctuation,
        _remove_nonalpha,
        _remove_accents,
    ]

    for func in clean_functions:
        text = func(text)
    return text.strip(" ")


def _lower(text: str) -> str:
    text = text.lower().replace("\n", " ")
    return text


def _remove_punctuation(text: str) -> str:
    for punctuation in string.punctuation:
        text = text.replace(punctuation, " ")
        text = re.sub(" +", " ", text)
    return text


def _remove_specialchar(text: str) -> str:
    return "".join(word for word in text if word.isalpha() or word == " ")


def _remove_nonalpha(text: str) -> str:
    text = "".join(c for c in text if c.isalpha() or c == " ")
    return re.sub(" +", " ", text)


def _remove_accents(text: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text)
        if unicodedata.category(c) != "Mn"
    )
