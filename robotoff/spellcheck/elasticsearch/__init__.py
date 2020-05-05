from typing import Dict
from pathlib import Path

from robotoff.spellcheck import BaseSpellchecker


class ElasticSearchSpellchecker(BaseSpellchecker):
    def __init__(self, index="product", confidence=1):
        self.index = index
        self.confidence = confidence

    @property
    def name(self):
        return (
            super(ElasticSearchSpellchecker, self).name
            + f"__index_{self.index}__conf_{self.confidence}"
        )

    def correct(self, txt: str) -> str:
        raise NotImplementedError
