import re

ASTERISK_SYMBOL = r"((\* ?=?|\(¹\)|\") ?)"
FROM_ORGANIC_FARMING_FR = r"issus? de l'agriculture (biologique|bio|durable)"
ORGANIC_MENTIONS_RE = re.compile(
    rf"{ASTERISK_SYMBOL}?ingr[ée]dients?( agricoles?)? {FROM_ORGANIC_FARMING_FR}"
    rf"|{ASTERISK_SYMBOL}?produits? {FROM_ORGANIC_FARMING_FR}"
    rf"|{ASTERISK_SYMBOL}?{FROM_ORGANIC_FARMING_FR}"
    rf"|{ASTERISK_SYMBOL}organic( farming)?",
    re.I,
)


def detect_additional_mentions(text: str, end_idx: int) -> int:
    """Detect additional mentions that are relevant to include in the
    ingredient list (such as organic/fair trade or allergen mentions) but
    that are not currently detected by the model (as the model was trained
    not to detect them).

    :param text: the full text to process
    :param end_idx: the end character index of the current ingredient list
    :return: the new end index of the ingredient list, if any mention was
        detected. Return the initial end index otherwise.
    """
    initial_end_idx = end_idx
    candidate = text[end_idx:]

    for char in candidate:
        if char.isspace() or char in (".", ","):
            end_idx += 1
        else:
            break

    matched = False
    candidate = text[end_idx:]

    if (match := ORGANIC_MENTIONS_RE.search(candidate)) is not None:
        if match.start() == 0:
            matched = True
            end_idx += match.end()

    # If a mention was detected, return the new end index
    if matched:
        return end_idx

    # If no mention was detected, reset the end index to its initial value
    return initial_end_idx
