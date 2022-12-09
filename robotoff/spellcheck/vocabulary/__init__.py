import re
from typing import Optional

from robotoff.spellcheck.base_spellchecker import BaseSpellchecker
from robotoff.spellcheck.vocabulary.utils import Vocabulary
from robotoff.utils.text import get_blank_nlp

TOKENS = list[str]
ADDITIVES_REGEX = re.compile(r"(?:E ?\d{3,5}[a-z]*)", re.IGNORECASE)
VERSION = "1"


class VocabularySpellchecker(BaseSpellchecker):
    def __init__(self):
        self.wikipedia_voc = Vocabulary("wikipedia_lower")
        self.ingredients_voc = Vocabulary("ingredients_fr_tokens") | Vocabulary(
            "ingredients_fr"
        )

    def correct(self, text: str) -> str:
        for token in self.tokenize(text, remove_additives=True):
            if all(c.isalpha() for c in token):
                if token not in self.wikipedia_voc:
                    suggestion: Optional[str] = self.ingredients_voc.suggest(token)
                    if suggestion is not None:
                        text = text.replace(token, suggestion)
        return text

    @staticmethod
    def tokenize(text: str, remove_additives: bool = False) -> TOKENS:
        tokens: TOKENS = []

        nlp = get_blank_nlp("fr")
        for token in nlp(text):
            tokens.append(token.orth_)
        tokens = [token for token in tokens if any(c.isalnum() for c in token)]
        if remove_additives:
            tokens = [token for token in tokens if ADDITIVES_REGEX.match(token) is None]
        return tokens

    def get_config(self):
        return {
            "version": VERSION,
            "name": self.__class__.__name__,
        }
