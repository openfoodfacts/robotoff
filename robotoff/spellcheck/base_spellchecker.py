import abc

from robotoff.spellcheck.items import SpellcheckItem


class BaseSpellchecker(metaclass=abc.ABCMeta):
    def predict(self, items: list[SpellcheckItem]) -> list[SpellcheckItem]:
        return [self.predict_one(item) for item in items]

    def predict_one(self, item: SpellcheckItem) -> SpellcheckItem:
        if item.is_lang_allowed:
            item.update_correction(
                correction=self.correct(item.latest_correction), model=self.name
            )
        return item

    @abc.abstractmethod
    def correct(self, text: str) -> str:
        pass

    @abc.abstractmethod
    def get_config(self):
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__
