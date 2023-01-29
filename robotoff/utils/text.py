import functools
import re
import unicodedata

import spacy

from robotoff.utils import get_logger

from .fold_to_ascii import fold, fold_without_replacement

logger = get_logger(__name__)

CONSECUTIVE_SPACES_REGEX = re.compile(r" {2,}")


def strip_accents_v1(s: str) -> str:
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


def strip_accents(s: str, keep_length: bool = True):
    """Strip accents and normalize string.

    :param keep_length: if True (default), no character is deleted without a
        subtitution of length 1: the length of the string is kept unchanged.
    """
    if keep_length:
        return fold_without_replacement(s)
    else:
        return fold(s)


def strip_consecutive_spaces(text: str) -> str:
    """Convert a sequence of 2+ spaces into a single space."""
    return CONSECUTIVE_SPACES_REGEX.sub(" ", text)


@functools.lru_cache()
def get_blank_nlp(lang: str) -> spacy.Language:
    """Return a blank (without model) spaCy language pipeline."""
    logger.info("Loading NLP for %s...", lang)
    return spacy.blank(lang)


@functools.lru_cache()
def get_lemmatizing_nlp(lang: str) -> spacy.Language:
    """Return a spaCy language pipeline with a lookup lemmatizer."""
    logger.info("Loading NLP with lemmatizer for %s...", lang)
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
    text = strip_accents(text)
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
