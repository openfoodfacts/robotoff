from typing import Optional

from robotoff.spellcheck import BaseSpellchecker
from robotoff.spellcheck.utils import tokenize_ingredients
from robotoff.spellcheck.vocabulary.utils import Vocabulary


class VocabularySpellchecker(BaseSpellchecker):
    def __init__(self):
        self.wikipedia_voc = Vocabulary("wikipedia_lower")
        self.ingredients_voc = Vocabulary("ingredients_fr_tokens") | Vocabulary(
            "ingredients_fr"
        )

    def correct(self, txt: str) -> str:
        for token in tokenize_ingredients(txt, remove_additives=True):
            if all(c.isalpha() for c in token):
                if not token in self.wikipedia_voc:
                    suggestion: Optional[str] = self.ingredients_voc.suggest(token)
                    if suggestion is not None:
                        txt = txt.replace(token, suggestion)
        return txt
