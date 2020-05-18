from typing import List, Dict
from dataclasses import asdict

from robotoff.spellcheck.items import SpellcheckItem
from robotoff.spellcheck.patterns import PatternsSpellchecker
from robotoff.spellcheck.percentages import PercentagesSpellchecker
from robotoff.spellcheck.vocabulary import VocabularySpellchecker
from robotoff.spellcheck.elasticsearch import ElasticSearchSpellchecker

from robotoff.spellcheck.exceptions import PipelineSpellcheckerException


class PipelineSpellchecker:

    SPELLCHECKERS = {
        "elasticsearch": ElasticSearchSpellchecker,
        "patterns": PatternsSpellchecker,
        "percentages": PercentagesSpellchecker,
        "vocabulary": VocabularySpellchecker,
    }

    def __init__(self):
        self.spellcheckers = []
        self.item = None

    def add_spellchecker(self, name: str, **kwargs) -> None:
        if name not in self.SPELLCHECKERS:
            raise ValueError(
                f"Spellchecker {name} not found. Available : {list(self.SPELLCHECKERS.keys())}"
            )
        self.spellcheckers.append(self.SPELLCHECKERS[name](**kwargs))

    def reset(self) -> None:
        self.item = None

    def correct(self, text: str) -> str:
        self.item = SpellcheckItem(text)
        if self.item.is_lang_allowed:
            for spellcheck in self.spellcheckers:
                spellcheck.predict([self.item])
        return self.item.latest_correction

    def get_corrections(self) -> List[Dict]:
        if self.item is None:
            raise PipelineSpellcheckerException(
                "You must process an item using 'correct' before attempting to run 'get_corrections'"
            )
        return [
            dict(asdict(atomic_correction), is_valid=atomic_correction.is_valid())
            for atomic_correction in self.item.all_atomic_corrections
        ]
