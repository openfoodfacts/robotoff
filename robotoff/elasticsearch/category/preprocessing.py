import re

from robotoff.utils.text import strip_consecutive_spaces

WEIGHT_REGEX = re.compile(
    r"[0-9]+[,.]?[0-9]*\s?(fl oz|dl|cl|mg|ml|lbs|oz|g|kg|l)(?![a-z])"
)

LABELS_REGEX = {
    "fr": re.compile(
        r"agriculture biologique|biologique|bio|igp|aop|aoc|label rouge"
        r"|commerce équitable"
    ),
    "en": re.compile(r"organic|pgi"),
    "es": re.compile(r"ecológico|ecológica|extra|comercio justo"),
    "de": re.compile(r"bio"),
    "nl": re.compile(r"bio"),
    "it": re.compile(
        r"biologica|biologico|commercio solidale|commercio equo e solidale"
        r"|da agricoltura biologica"
    ),
}

EXTRAWORDS_REGEX = {
    "fr": re.compile(r"gourmand|délicieux"),
    "en": re.compile(r"delicious"),
}
BRANDS_REGEX = re.compile(r"k bio|ja!|coop|belvita|carrefour|auchan|danone")


def preprocess_name(name: str, lang: str) -> str:
    """Preprocess category name before matching:
    - remove all weight mentions (100 g, 1l,...)
    - remove all label mentions (IGP, AOP, Label Rouge,...)

    This preprocessing step increases recall, while not decreasing
    precision."""
    name = name.lower()
    name = remove_weights(name)
    name = remove_brands(name)
    name = remove_labels(name, lang)
    name = remove_marketing_words(name, lang)
    name = strip_consecutive_spaces(name)
    name = name.strip()
    return name


def remove_weights(name: str) -> str:
    return WEIGHT_REGEX.sub("", name)


def remove_brands(name: str) -> str:
    return BRANDS_REGEX.sub("", name)


def remove_marketing_words(name: str, lang: str) -> str:
    if lang in EXTRAWORDS_REGEX:
        name = EXTRAWORDS_REGEX[lang].sub("", name)

    return name


def remove_labels(name: str, lang: str) -> str:
    if lang in LABELS_REGEX:
        name = LABELS_REGEX[lang].sub("", name)

    return name
