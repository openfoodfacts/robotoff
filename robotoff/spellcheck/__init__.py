from typing import List
from robotoff.spellcheck.data_utils import SpellcheckItem


class BaseSpellchecker:
    def predict(self, items: List[SpellcheckItem]) -> List[SpellcheckItem]:
        return [self.predict_one(item) for item in items]

    def predict_one(self, item: SpellcheckItem) -> SpellcheckItem:
        item.update_correction(
            correction=self.correct(item.latest_correction), model=self.name
        )
        return item

    def correct(self, text: str) -> str:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__
