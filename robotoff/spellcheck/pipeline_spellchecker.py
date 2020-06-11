from robotoff.spellcheck.items import SpellcheckItem
from robotoff.spellcheck.patterns import PatternsSpellchecker
from robotoff.spellcheck.percentages import PercentagesSpellchecker
from robotoff.spellcheck.vocabulary import VocabularySpellchecker
from robotoff.spellcheck.elasticsearch import ElasticSearchSpellchecker


class PipelineSpellchecker:

    SPELLCHECKERS = {
        "elasticsearch": ElasticSearchSpellchecker,
        "patterns": PatternsSpellchecker,
        "percentages": PercentagesSpellchecker,
        "vocabulary": VocabularySpellchecker,
    }

    def __init__(self):
        self.spellcheckers = []

    def add_spellchecker(self, name: str, **kwargs) -> None:
        if name not in self.SPELLCHECKERS:
            raise ValueError(
                f"Spellchecker {name} not found. Available : {list(self.SPELLCHECKERS.keys())}"
            )
        self.spellcheckers.append(self.SPELLCHECKERS[name](**kwargs))

    def correct(self, text: str) -> SpellcheckItem:
        item = SpellcheckItem(text)
        if item.is_lang_allowed:
            for spellcheck in self.spellcheckers:
                spellcheck.predict([item])
        return item
