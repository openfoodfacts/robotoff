import re
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
                    self.patterns[line] = current_pattern

    @property
    def name(self):
        return super(PatternsSpellchecker, self).name + "__" + self.lang

    def correct(self, text: str) -> str:
        for pattern, replacement in self.patterns.items():
            text = replace_keep_case(pattern, replacement, text)
        return text


def replace_keep_case(word, replacement, text):
    """
    Taken from https://stackoverflow.com/a/24894475/5333945
    Replace a word in a text while preserving the case.
    """

    def func(match):
        g = match.group()
        if g.islower():
            return replacement.lower()
        if g.istitle():
            return replacement.title()
        if g.isupper():
            return replacement.upper()
        return replacement

    return re.sub(word, func, text, flags=re.IGNORECASE)
