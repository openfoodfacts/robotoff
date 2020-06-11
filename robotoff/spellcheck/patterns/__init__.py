from typing import Dict
from pathlib import Path

from robotoff.settings import SPELLCHECK_PATTERNS_PATHS
from robotoff.spellcheck.base_spellchecker import BaseSpellchecker

Patterns = Dict[str, str]


class PatternsSpellchecker(BaseSpellchecker):
    def __init__(self, lang: str = "fr"):
        self.lang = lang
        self.patterns: Patterns = {}

        with SPELLCHECK_PATTERNS_PATHS[lang].open() as f:
            current_pattern = None
            for line in f:
                line = line.strip().split("#")[0]
                if len(line) == 0:
                    current_pattern = None
                elif current_pattern is None:
                    current_pattern = line
                else:
                    self.patterns[line.lower()] = current_pattern.lower()
                    self.patterns[line.upper()] = current_pattern.upper()
                    self.patterns[line.capitalize()] = current_pattern.capitalize()
                    self.patterns[line] = current_pattern

    @property
    def name(self):
        return super(PatternsSpellchecker, self).name + "__" + self.lang

    def correct(self, text: str) -> str:
        for key, value in self.patterns.items():
            text = text.replace(key, value)
        return text
