import re
import unicodedata


CONSECUTIVE_SPACES_REGEX = re.compile(r" {2,}")


def strip_accents_ascii(s):
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
    nkfd_form = unicodedata.normalize('NFKD', s)
    return nkfd_form.encode('ASCII', 'ignore').decode('ASCII')


def strip_consecutive_spaces(text: str) -> str:
    """Convert a sequence of 2+ spaces into a single space."""
    return CONSECUTIVE_SPACES_REGEX.sub(' ', text)
