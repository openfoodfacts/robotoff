from robotoff.settings import FR_TOKENS_PATH, INGREDIENT_TOKENS_PATH
from robotoff.utils import cache, text_file_iter


def get_fr_known_tokens() -> set[str]:
    tokens = set(text_file_iter(INGREDIENT_TOKENS_PATH, comment=False))
    tokens = tokens.union(set(text_file_iter(FR_TOKENS_PATH, comment=False)))
    return tokens


FR_KNOWN_TOKENS_CACHE = cache.CachedStore(get_fr_known_tokens)
