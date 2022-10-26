import functools
import re
import unicodedata

import spacy

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


@functools.lru_cache()
def get_blank_nlp(lang: str) -> spacy.Language:
    """Return a blank (without model) spaCy language pipeline."""
    return spacy.blank(lang)


@functools.lru_cache()
def get_lemmatizing_nlp(lang: str) -> spacy.Language:
    """Return a spaCy language pipeline with a lookup lemmatizer."""
    nlp = spacy.blank(lang)
    nlp.add_pipe("lemmatizer", config={"mode": "lookup"})
    nlp.initialize()
    return nlp


def get_tag(text: str) -> str:
    """Return a tag from a text.

    In Open Food Facts, tags are obtained from free text by performing the
    following:
    - lowercasing
    - accent removal
    - replacement of punctuation by either a comma ("-") or nothing, depending
    on the punctuation
    """
    text = strip_accents_ascii_v2(text)
    text = (
        text.lower()
        .replace(" & ", "-")
        .replace(" ", "-")
        .replace("'", "-")
        .replace(".", "-")
        .replace("!", "")
        .replace("?", "")
    )
    return strip_consecutive_spaces(text).strip("-")
