from typing import Dict
from pathlib import Path

from robotoff.spellcheck import BaseSpellchecker

Patterns = Dict[str, str]


class PatternsSpellchecker(BaseSpellchecker):

    PATTERNS_PATHS = {"fr": Path(__file__).parent / "patterns_fr.txt"}

    def __init__(self, lang: str = "fr"):
        self.lang = lang
        self.patterns: Patterns = {}

        with self.PATTERNS_PATHS[lang].open() as f:
            current_pattern = None
            for line in f.readlines():
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

    def correct(self, txt: str) -> str:
        for key, value in self.patterns.items():
            txt = txt.replace(key, value)
        return txt
