import operator
from typing import List, Iterable
from dataclasses import dataclass, field, InitVar

from robotoff.utils.text import FR_NLP_CACHE, FR_KNOWN_TOKENS_CACHE


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
    score: int = None
    model: str = None

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
        nlp = FR_NLP_CACHE.get()
        known_tokens = FR_KNOWN_TOKENS_CACHE.get()

        for token in nlp(self.original):
            if token.lower_ not in known_tokens:
                return False
        return True


@dataclass
class SpellcheckIteration:
    original: str
    model: str = None
    correction: InitVar[str] = None
    atomic_corrections: List[AtomicCorrection] = field(default_factory=list)

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
            valid_atomic_corrections, key=operator.attrgetter("offset"),
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
        self.original = original
        self.iterations = []

    @property
    def latest_correction(self) -> str:
        if len(self.iterations) > 0:
            return self.iterations[-1].corrected_text
        else:
            return self.original

    @property
    def all_atomic_corrections(self) -> List[AtomicCorrection]:
        return [
            atomic_correction
            for iteration in self.iterations
            for atomic_correction in iteration.atomic_corrections
        ]

    def update_correction(self, correction: str, model: str = "UNK"):
        self.iterations.append(
            SpellcheckIteration(
                original=self.latest_correction, correction=correction, model=model,
            )
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
