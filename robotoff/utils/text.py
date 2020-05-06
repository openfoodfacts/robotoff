import functools
import re
import unicodedata
from typing import List, Set

from spacy.lang.en import English
from spacy.lang.fr import French

from robotoff import settings
from robotoff.utils import text_file_iter, cache

CONSECUTIVE_SPACES_REGEX = re.compile(r" {2,}")


def strip_accents_ascii(s: str) -> str:
    """Transform accentuated unicode symbols into ascii or nothing

    Warning: this solution is only suited for languages that have a direct
    transliteration to ASCII symbols.

    Parameters
    ----------
    s : string
        The string to strip

    See also
    --------
    strip_accents_unicode
        Remove accentuated char for any unicode symbol.
    """
    nkfd_form = unicodedata.normalize("NFKD", s)
    return nkfd_form.encode("ASCII", "ignore").decode("ASCII")


def strip_consecutive_spaces(text: str) -> str:
    """Convert a sequence of 2+ spaces into a single space."""
    return CONSECUTIVE_SPACES_REGEX.sub(" ", text)


def get_nlp(lang: str):
    if lang == "fr":
        return French()
    elif lang == "en":
        return English()
    else:
        raise ValueError("unknown lang: {}".format(lang))


FR_NLP_CACHE = cache.CachedStore(
    functools.partial(get_nlp, lang="fr"), expiration_interval=None
)


def get_fr_known_tokens() -> Set[str]:
    tokens = set(text_file_iter(settings.INGREDIENT_TOKENS_PATH, comment=False))
    tokens = tokens.union(set(text_file_iter(settings.FR_TOKENS_PATH, comment=False)))
    return tokens


FR_KNOWN_TOKENS_CACHE = cache.CachedStore(get_fr_known_tokens)
