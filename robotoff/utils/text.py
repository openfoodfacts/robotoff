import functools
import re
import unicodedata

from spacy.lang.en import English
from spacy.lang.fr import French

from robotoff.utils import cache

from .fold_to_ascii import fold

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


def strip_accents_ascii_v2(s):
    return fold(s)


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


def get_tag(text: str) -> str:
    text = strip_accents_ascii_v2(text)
    return (
        text.lower()
        .replace(" & ", "-")
        .replace(" ", "-")
        .replace("'", "-")
        .replace(".", "-")
    )


FR_NLP_CACHE = cache.CachedStore(
    functools.partial(get_nlp, lang="fr"), expiration_interval=None
)
