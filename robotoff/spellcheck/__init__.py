import dataclasses
from typing import List


@dataclasses.dataclass
class SpellcheckIteration:
    model: str
    original: str
    correction: str


class SpellcheckItem:
    def __init__(self, original: str):
        self.original = original
        self.iterations = []

    @property
    def latest_correction(self) -> str:
        if len(self.iterations) > 0:
            return self.iterations[-1].correction
        else:
            return self.original

    def update_correction(self, correction: str, model: str = "UNK"):
        self.iterations.append(
            SpellcheckIteration(
                original=self.latest_correction, correction=correction, model=model,
            )
        )


class BaseSpellchecker:
    def predict(self, items: List[SpellcheckItem]) -> List[SpellcheckItem]:
        return [self.predict_one(item) for item in items]

    def predict_one(self, item: SpellcheckItem) -> SpellcheckItem:
        item.update_correction(
            correction=self.correct(item.latest_correction), model=self.name
        )
        return item

    def correct(self, txt: str) -> str:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__
