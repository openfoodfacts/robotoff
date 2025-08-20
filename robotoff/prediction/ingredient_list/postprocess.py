import functools
import re

from lark import Discard, Lark, Transformer

from robotoff import settings
from robotoff.utils.cache import function_cache_register

ASTERISK_SYMBOL = r"((\* ?=?|\(¹\)|\") ?)"
FROM_ORGANIC_FARMING_FR = r"issus? de l'agriculture (biologique|bio|durable)"
ORGANIC_MENTIONS_RE = re.compile(
    # fr
    rf"{ASTERISK_SYMBOL}?ingr[ée]dients?( agricoles?)? {FROM_ORGANIC_FARMING_FR}"
    rf"|{ASTERISK_SYMBOL}?produits? {FROM_ORGANIC_FARMING_FR}"
    rf"|{ASTERISK_SYMBOL}?{FROM_ORGANIC_FARMING_FR}"
    # en
    rf"|{ASTERISK_SYMBOL}organic( farming)?"
    # de
    rf"|{ASTERISK_SYMBOL}?aus biologischer landwirtschaft"
    # es
    rf"|{ASTERISK_SYMBOL}?procedentes del cultivo ecol[óo]gico"
    rf"|{ASTERISK_SYMBOL}?de cultivo ecol[óo]gico certificado"
    rf"|{ASTERISK_SYMBOL}?ingredientes? ecol[óo]gicos?"
    # it
    rf"|{ASTERISK_SYMBOL}?biologico",
    re.I,
)


def detect_additional_mentions(text: str, end_idx: int) -> int:
    """Detect additional mentions that are relevant to include in the
    ingredient list (such as organic/fair trade or allergen mentions) but
    that are not currently detected by the model (as the model was trained
    not to include them in the ingredient list).

    :param text: the full text to process
    :param end_idx: the end character index of the current ingredient list
    :return: the new end index of the ingredient list, if any mention was
        detected. Return the initial end index otherwise.
    """
    initial_end_idx = end_idx
    last_updated = True
    matched = False

    while last_updated:
        last_updated = False
        lookup_end_idx = end_idx
        candidate = text[lookup_end_idx:]

        for char in candidate:
            if char.isspace() or char in (".", ","):
                lookup_end_idx += 1
            else:
                break

        candidate = text[lookup_end_idx:]

        if (match := ORGANIC_MENTIONS_RE.search(candidate)) is not None:
            if match.start() == 0:
                matched = True
                last_updated = True
                lookup_end_idx += match.end()
                end_idx = lookup_end_idx

        if (
            new_end_idx := detect_trace_mention(text, lookup_end_idx)
        ) != lookup_end_idx:
            matched = True
            lookup_end_idx = new_end_idx
            end_idx = new_end_idx
            last_updated = True

    # If a mention was detected, return the new end index
    if matched:
        return end_idx

    # If no mention was detected, reset the end index to its initial value
    return initial_end_idx


@functools.cache
def load_trace_grammar() -> Lark:
    return Lark.open(
        str(settings.GRAMMARS_DIR / "traces.lark"),
        start="start",
        # include start and end positions in the parse tree
        propagate_positions=True,
    )


class TraceDetectionTransformer(Transformer):
    """Transformer to detect trace mentions in the ingredient list.

    Only the start and end positions of the first item are returned,
    as we're only interested in the end position of the first trace mention.
    Start position is returned to make sure that the match is at the start of
    the text.
    """

    def start(self, items: list):
        if items:
            return items[0]
        return None, None

    def value(self, items: list):
        return items

    def traces(self, items):
        item = items[0]
        return item.meta.start_pos, item.meta.end_pos

    def WS(self, token):
        return Discard

    def OTHER(self, token):
        return Discard

    def junk(self, items):
        return Discard


def detect_trace_mention(text: str, end_idx: int) -> int:
    """Detect trace mentions that are relevant to include in the ingredient
    list.

    :param text: the full text to process
    :param end_idx: the end character index of the current ingredient list
    :return: the new end index of the ingredient list, if any mention was
        detected, or the initial end index otherwise
    """
    if not text[end_idx:]:
        return end_idx

    initial_end_idx = end_idx
    grammar = load_trace_grammar()
    t = grammar.parse(text[end_idx:].lower())
    start_idx, end_idx_offset = TraceDetectionTransformer().transform(t)

    if start_idx != 0:
        return initial_end_idx

    end_idx += end_idx_offset
    return end_idx


function_cache_register.register(load_trace_grammar)
