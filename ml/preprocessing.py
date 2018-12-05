import re
from sklearn.feature_extraction.text import strip_accents_ascii

PUNCTUATION_REGEX = re.compile(r"""[:,;.&~"'|`_\\={}%()\[\]]+""")
DIGIT_REGEX = re.compile(r"[0-9]+")
MULTIPLE_SPACES_REGEX = re.compile(r" +")

def preprocess(text):
    text = strip_accents_ascii(text)
    text = text.lower()
    text = PUNCTUATION_REGEX.sub(' ', text)
    text = DIGIT_REGEX.sub(' ', text)
    return MULTIPLE_SPACES_REGEX.sub(' ', text)

