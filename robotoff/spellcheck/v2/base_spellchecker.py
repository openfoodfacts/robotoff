from typing import List
from dataclasses import asdict

from robotoff.spellcheck.v2.items import SpellcheckItem


class BaseSpellchecker:
    def predict(self, items: List[SpellcheckItem]) -> List[SpellcheckItem]:
        return [self.predict_one(item) for item in items]

    def predict_one(self, item: SpellcheckItem) -> SpellcheckItem:
        if item.is_lang_allowed:
            item.update_correction(
                correction=self.correct(item.latest_correction), model=self.name
            )
        return item

    def correct(self, text: str) -> str:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__
