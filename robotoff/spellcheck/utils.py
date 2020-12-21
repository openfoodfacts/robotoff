from typing import Set

from robotoff.settings import INGREDIENT_TOKENS_PATH, FR_TOKENS_PATH
from robotoff.utils import text_file_iter, cache


def get_fr_known_tokens() -> Set[str]:
    tokens = set(text_file_iter(INGREDIENT_TOKENS_PATH, comment=False))
    tokens = tokens.union(set(text_file_iter(FR_TOKENS_PATH, comment=False)))
    return tokens


FR_KNOWN_TOKENS_CACHE = cache.CachedStore(get_fr_known_tokens)
