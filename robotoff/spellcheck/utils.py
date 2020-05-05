import re
from typing import List, Dict

from spacy.lang.fr import French

TOKENS = List[str]

# Food additives (EXXX) may be mistaken from one another, because of their edit distance proximity
ADDITIVES_REGEX = re.compile("(?:E ?\d{3,5}[a-z]*)", re.IGNORECASE)


FR_NLP = French()


def normalize_ingredients(ingredients: str) -> str:
    normalized = ingredients.lower()
    normalized = normalized.replace("œu", "oeu")
    normalized = normalized.replace("’", "'")
    return normalized


def tokenize_ingredients(text: str, remove_additives: bool = False) -> TOKENS:
    tokens: TOKENS = []
    for token in FR_NLP(text):
        tokens.append(token.orth_)
    tokens = [token for token in tokens if any(c.isalnum() for c in token)]
    if remove_additives:
        tokens = [token for token in tokens if ADDITIVES_REGEX.match(token) is None]
    return tokens
