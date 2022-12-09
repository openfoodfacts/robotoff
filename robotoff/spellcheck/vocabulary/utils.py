from collections import defaultdict
from pathlib import Path
from typing import AbstractSet, Callable, Optional

from robotoff.settings import (
    FR_TOKENS_PATH,
    INGREDIENT_TOKENS_PATH,
    INGREDIENTS_FR_PATH,
)
from robotoff.utils import text_file_iter
from robotoff.utils.cache import CachedStore

DEACCENTED_TOKENS = dict[str, list[str]]


class Vocabulary(object):
    def __init__(
        self,
        voc_name: Optional[str] = None,
        tokens: Optional[AbstractSet] = None,
        deaccented_tokens: Optional[DEACCENTED_TOKENS] = None,
    ):
        self.voc = set()

        if voc_name is not None:
            self.voc = VOC_CACHE[
                voc_name
            ].get()  # CACHE is defined after Vocabulary class

        if tokens is not None:
            self.voc.update(tokens)

        if voc_name is not None:
            assert deaccented_tokens is None
            self.deaccented_tokens = DEACCENTED_TOKENS_CACHE[voc_name].get()
        elif deaccented_tokens is not None:
            self.deaccented_tokens = defaultdict(list, deaccented_tokens)
        else:
            self.deaccented_tokens = self.deaccent_tokens_fn(self.voc)()

    def __contains__(self, token: str) -> bool:
        return self.normalize(token) in self.voc

    def _contains_deaccent(self, token: str) -> bool:
        return self.deaccent(token) in self.deaccented_tokens

    def __or__(self, other):
        return Vocabulary(
            tokens=self.voc | other.voc,
            deaccented_tokens=defaultdict(
                list, dict(self.deaccented_tokens, **other.deaccented_tokens)
            ),
        )

    def suggest(self, token: str) -> Optional[str]:
        deaccent_suggestions: Optional[list[str]] = self._suggest_deaccent(token)
        if deaccent_suggestions is not None:
            if len(deaccent_suggestions) == 1:
                return deaccent_suggestions[0]
            elif len(deaccent_suggestions) > 1:
                return None

        split_suggestions: list[tuple[str, str]] = self._suggest_split(token)
        if len(split_suggestions) == 1:
            return split_suggestions[0][0] + " " + split_suggestions[0][1]
        return None

    def _suggest_deaccent(self, token: str) -> Optional[list[str]]:
        if token in self:
            return None
        deaccented_token = self.deaccent(token)
        if deaccented_token in self.deaccented_tokens:
            return self.deaccented_tokens[deaccented_token]
        return None

    def _suggest_split(self, token: str) -> list[tuple[str, str]]:
        if token in self:
            return []

        suggestions = []
        for i in range(2, len(token) - 1):
            # pre and post must be at least 2 letters long
            pre = token[:i]
            post = token[i:]
            if pre in self and post in self or (pre + " " + post) in self:
                suggestions.append((pre, post))
            else:
                if self._contains_deaccent(pre) and post in self:
                    pre_suggestion = self.deaccented_tokens[self.deaccent(pre)]
                    if len(pre_suggestion) == 1:
                        suggestions.append((pre_suggestion[0], post))

                if pre in self and self._contains_deaccent(post):
                    post_suggestion = self.deaccented_tokens[self.deaccent(post)]
                    if len(post_suggestion) == 1:
                        suggestions.append((pre, post_suggestion[0]))

                if self._contains_deaccent(pre) and self._contains_deaccent(post):
                    pre_suggestion = self.deaccented_tokens[self.deaccent(pre)]
                    post_suggestion = self.deaccented_tokens[self.deaccent(post)]
                    if len(pre_suggestion) == 1 and len(post_suggestion) == 1:
                        suggestions.append((pre_suggestion[0], post_suggestion[0]))
        return suggestions

    @staticmethod
    def deaccent(token: str) -> str:
        ACCENTS = {"a": "à", "e": "éêè", "u": "ùüû", "i": "ïî"}
        for letter in ACCENTS:
            for c in ACCENTS[letter]:
                token = token.replace(c, letter)
        return token

    @staticmethod
    def normalize(token: str) -> str:
        return token.lower()

    @classmethod
    def load_vocabulary_fn(cls, voc_path: Path) -> Callable[[], AbstractSet[str]]:
        def inner_fn() -> AbstractSet[str]:
            return set(cls.normalize(token) for token in text_file_iter(voc_path))

        return inner_fn

    @classmethod
    def deaccent_tokens_fn(cls, voc: AbstractSet) -> Callable[[], DEACCENTED_TOKENS]:
        def inner_fn() -> DEACCENTED_TOKENS:
            deaccented_tokens = defaultdict(list)
            for token in voc:
                deaccented_token = cls.deaccent(token)
                if deaccented_token != token:
                    deaccented_tokens[deaccented_token].append(token)
            return deaccented_tokens

        return inner_fn


def get_voc_cache(path: Path) -> CachedStore:
    return CachedStore(Vocabulary.load_vocabulary_fn(path))


def get_deaccent_cache(voc_cache: CachedStore) -> CachedStore:
    return CachedStore(Vocabulary.deaccent_tokens_fn(voc_cache.get()))


VOC_CACHE: dict[str, CachedStore] = {
    "wikipedia_lower": get_voc_cache(FR_TOKENS_PATH),
    "ingredients_fr": get_voc_cache(INGREDIENTS_FR_PATH),
    "ingredients_fr_tokens": get_voc_cache(INGREDIENT_TOKENS_PATH),
}

DEACCENTED_TOKENS_CACHE: dict[str, CachedStore] = {}
for key, voc_cache in VOC_CACHE.items():
    DEACCENTED_TOKENS_CACHE[key] = get_deaccent_cache(voc_cache)
