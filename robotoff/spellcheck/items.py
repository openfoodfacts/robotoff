import operator
import re
from dataclasses import InitVar, asdict, dataclass, field
from typing import Iterable, Optional

from robotoff.prediction.langid import DEFAULT_LANGUAGE_IDENTIFIER, LanguageIdentifier
from robotoff.spellcheck.utils import FR_KNOWN_TOKENS_CACHE
from robotoff.utils.text import get_blank_nlp

LANGUAGE_ALLOWED = "fr"
LANGUAGE_IDENTIFIER: LanguageIdentifier = DEFAULT_LANGUAGE_IDENTIFIER.get()

# Food additives (EXXX) may be mistaken from one another, because of their edit distance proximity
BLACKLIST_RE = re.compile(r"(?:\d+(?:[,.]\d+)?\s*%)|(?:[0-9])(?![\w-])")
PUNCTUATION_BLACKLIST_RE = re.compile(r"[_•:]")
E_BLACKLIST_RE = re.compile(r"(?<!\w)(?:E ?\d{3,5}[a-z]*)")
SPLITTER_CHAR = {"(", ")", ",", ";", "[", "]", "-", "{", "}"}


@dataclass
class Offset:
    start: int
    end: int

    def __lt__(self, other):
        return self.start < other.start


@dataclass
class AtomicCorrection:
    original: str
    correction: str
    offset: Offset
    force_valid: bool = False
    score: Optional[int] = None
    model: Optional[str] = None

    def is_valid(self, plural: bool = True, original_known: bool = True) -> bool:
        if self.force_valid:
            return True

        if plural and self._is_plural():
            return False

        if original_known and self._is_original_known():
            return False

        # Tokens with numbers are tricky to correct
        if any(x.isdigit() for x in self.correction):
            return False

        return True

    def has_difference(self) -> bool:
        return self.correction != self.original

    def _is_plural(self) -> bool:
        original_str = self.original.lower()
        correction_str = self.correction.lower()
        return (
            original_str.endswith("s")
            and correction_str == original_str[:-1]
            or correction_str.endswith("s")
            and original_str == correction_str[:-1]
        )

    def _is_original_known(self) -> bool:
        nlp = get_blank_nlp("fr")
        known_tokens = FR_KNOWN_TOKENS_CACHE.get()

        for token in nlp(self.original):
            if token.lower_ not in known_tokens:
                return False
        return True


@dataclass
class SpellcheckIteration:
    original: str
    model: Optional[str] = None
    correction: InitVar[Optional[str]] = None
    atomic_corrections: list[AtomicCorrection] = field(default_factory=list)

    def __post_init__(self, correction: str):
        if correction is not None:
            self.add_full_correction(correction)

    @property
    def corrected_text(self) -> str:
        valid_atomic_corrections = [
            correction
            for correction in self.atomic_corrections
            if correction.is_valid()
        ]

        if not valid_atomic_corrections:
            return self.original

        sorted_atomic_corrections = sorted(
            valid_atomic_corrections,
            key=operator.attrgetter("offset"),
        )

        last_correction = None
        corrected_fragments = []
        for atomic_correction in sorted_atomic_corrections:
            if last_correction is None:
                corrected_fragments.append(
                    self.original[: atomic_correction.offset.start]
                )
            else:
                corrected_fragments.append(
                    self.original[
                        last_correction.offset.end : atomic_correction.offset.start
                    ]
                )
            corrected_fragments.append(atomic_correction.correction)
            last_correction = atomic_correction

        if last_correction is not None:
            corrected_fragments.append(self.original[last_correction.offset.end :])

        return "".join(corrected_fragments)

    def add_atomic_correction(
        self, correction: str, offset: Offset, score: int
    ) -> None:
        self.atomic_corrections.append(
            AtomicCorrection(
                original=self.original[offset.start : offset.end],
                correction=correction,
                offset=offset,
                score=score,
                model=self.model,
            )
        )

    def add_full_correction(self, correction: str) -> None:
        assert len(self.atomic_corrections) == 0
        self.atomic_corrections = [
            AtomicCorrection(
                original=self.original,
                correction=correction,
                offset=Offset(0, len(self.original)),
                force_valid=True,
                model=self.model,
            )
        ]


class SpellcheckItem:
    def __init__(self, original: str):
        self.iterations: list[SpellcheckIteration] = []
        self.original: str = original
        self.is_lang_allowed: bool = self.__is_lang_allowed()

    @property
    def latest_correction(self) -> str:
        if len(self.iterations) > 0:
            return self.iterations[-1].corrected_text
        else:
            return self.original

    @property
    def corrections(self) -> list[dict]:
        return [
            dict(asdict(atomic_correction), is_valid=atomic_correction.is_valid())
            for atomic_correction in self.all_atomic_corrections
            if atomic_correction.has_difference()
        ]

    @property
    def all_atomic_corrections(self) -> list[AtomicCorrection]:
        return [
            atomic_correction
            for iteration in self.iterations
            for atomic_correction in iteration.atomic_corrections
        ]

    def __is_lang_allowed(self) -> bool:
        languages = LANGUAGE_IDENTIFIER.predict(self.original.lower(), threshold=0.5)
        if len(languages) == 0:
            return True
        return languages[0].lang == LANGUAGE_ALLOWED

    def update_correction(self, correction: str, model: str = "UNK"):
        self.iterations.append(
            SpellcheckIteration(
                original=self.latest_correction,
                correction=correction,
                model=model,
            )
        )


@dataclass
class Ingredients:
    text: str
    normalized_text: str
    offsets: list[Offset] = field(default_factory=list)

    def __iter__(self) -> Iterable[str]:
        yield from self.get_iter()

    def get_iter(self) -> Iterable[str]:
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

    @classmethod
    def from_text(cls, text: str, remove_blacklist: bool = True):
        if remove_blacklist:
            normalized_text = cls.process_remove_blacklist(text)
        else:
            normalized_text = text

        offsets = []
        chars = []
        start_idx = 0

        for idx, char in enumerate(normalized_text):
            if char in SPLITTER_CHAR:
                offsets.append(Offset(start_idx, idx))
                start_idx = idx + 1
                chars.append(" ")
            else:
                chars.append(char)

        if start_idx != len(normalized_text):
            offsets.append(Offset(start_idx, len(normalized_text)))

        normalized_text = "".join(chars)
        return cls(text, normalized_text, offsets)

    @classmethod
    def process_remove_blacklist(cls, text: str) -> str:
        text_without_blacklist = text

        for regex in (E_BLACKLIST_RE, BLACKLIST_RE, PUNCTUATION_BLACKLIST_RE):
            while True:
                try:
                    match = next(regex.finditer(text_without_blacklist))
                except StopIteration:
                    break
                if match:
                    start = match.start()
                    end = match.end()
                    text_without_blacklist = (
                        text_without_blacklist[:start]
                        + " " * (end - start)
                        + text_without_blacklist[end:]
                    )
                else:
                    break

        return text_without_blacklist
