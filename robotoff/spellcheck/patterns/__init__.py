import re

from robotoff.settings import SPELLCHECK_PATTERNS_PATHS
from robotoff.spellcheck.base_spellchecker import BaseSpellchecker
from robotoff.spellcheck.exceptions import LanguageNotAllowedException

Patterns = dict[str, str]

VERSION = "1"


class PatternsSpellchecker(BaseSpellchecker):
    def __init__(self, lang: str = "fr"):
        self.lang = lang
        self.patterns: Patterns = {}

        try:
            patterns_path = SPELLCHECK_PATTERNS_PATHS[lang]
        except KeyError:
            raise LanguageNotAllowedException(
                f"Lang {lang} is not supported in PatternsSpellchecker."
                f" Allowed : {list(SPELLCHECK_PATTERNS_PATHS.keys())}."
            )

        with patterns_path.open() as f:
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

    def get_config(self):
        return {
            "version": VERSION,
            "name": self.__class__.__name__,
        }


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
