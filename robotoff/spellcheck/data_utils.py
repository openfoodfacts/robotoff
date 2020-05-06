from typing import List, Iterable
from dataclasses import dataclass, field

from robotoff.utils.text import FR_NLP_CACHE, FR_KNOWN_TOKENS_CACHE


class TokenLengthMismatchException(Exception):
    pass


@dataclass
class Offset:
    start: int
    end: int


@dataclass
class TermCorrection:
    original: str
    correction: str
    offset: Offset

    def is_valid(self, plural: bool = True, original_known: bool = True) -> bool:
        if plural and self._is_plural():
            return False

        if original_known and self._is_original_known():
            return False

        # Tokens with numbers are tricky to correct
        if any(x.isdigit() for x in self.correction):
            return False

        return True

    def _is_plural(self) -> bool:
        original_str = self.original.lower()
        correction_str = self.correction.lower()
        return (
            original_str.endswith("s")
            and correction_str == original_str[:-1]
            or correction_str.endswith("s")
            and original_str == correction_str[:-1]
        )

    def _is_original_known(text: str):
        nlp = FR_NLP_CACHE.get()
        known_tokens = FR_KNOWN_TOKENS_CACHE.get()

        for token in nlp(text):
            if token.lower_ not in known_tokens:
                return False
        return True


@dataclass
class Correction:
    term_corrections: List[TermCorrection]
    score: int

    def add_term(self, original: str, correction: str, offset: Offset):
        self.term_corrections.append(
            TermCorrection(original=original, correction=correction, offset=offset)
        )


@dataclass
class Ingredients:
    text: str
    normalized_text: str
    offsets: List[Offset] = field(default_factory=list)

    def __iter__(self) -> Iterable[str]:
        for index, _ in enumerate(self.offsets):
            yield self.get_normalized_ingredient_text(index)

    def get_ingredient_text(self, index: int) -> str:
        offset = self.offsets[index]
        return self.text[offset.start : offset.end]

    def get_normalized_ingredient_text(self, index: int) -> str:
        offset = self.offsets[index]
        return self.normalized_text[offset.start : offset.end]

    def count(self) -> int:
        return len(self.offsets)
