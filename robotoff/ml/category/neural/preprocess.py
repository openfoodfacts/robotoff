import re

from robotoff.utils.text import strip_accents_ascii

PUNCTUATION_REGEX = re.compile(r"""[:,;.&~"'|`_\\={}%()\[\]]+""")
DIGIT_REGEX = re.compile(r"[0-9]+")
MULTIPLE_SPACES_REGEX = re.compile(r" +")


def preprocess_product_name(
    text: str, lower: bool, strip_accent: bool, remove_punct: bool, remove_digit: bool
) -> str:
    if strip_accent:
        text = strip_accents_ascii(text)

    if lower:
        text = text.lower()

    if remove_punct:
        text = PUNCTUATION_REGEX.sub(" ", text)

    if remove_digit:
        text = DIGIT_REGEX.sub(" ", text)

    return MULTIPLE_SPACES_REGEX.sub(" ", text)


def tokenize(text: str, nlp):
    return [token.orth_ for token in nlp(text)]
