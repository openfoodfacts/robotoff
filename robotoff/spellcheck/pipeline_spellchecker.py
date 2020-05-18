from dataclasses import asdict
from typing import List, Dict, Optional

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

    def correct(self, text: Optional[str] = None) -> str:
        if text is not None:
            self._process(text)
        if self.item is None:
            raise PipelineSpellcheckerException("No text processed.")
        return self.item.latest_correction

    def get_corrections(self, text: Optional[str] = None) -> List[Dict]:
        if text is not None:
            self._process(text)
        if self.item is None:
            raise PipelineSpellcheckerException("No text processed.")
        return [
            dict(asdict(atomic_correction), is_valid=atomic_correction.is_valid())
            for atomic_correction in self.item.all_atomic_corrections
            if atomic_correction.has_difference()
        ]

    def _process(self, text: str) -> None:
        self.item = SpellcheckItem(text)
        if self.item.is_lang_allowed:
            for spellcheck in self.spellcheckers:
                spellcheck.predict([self.item])
