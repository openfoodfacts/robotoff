import itertools
import re
import string
from collections import defaultdict
from pathlib import Path
from typing import Optional

import cachetools
from flashtext import KeywordProcessor

from robotoff.taxonomy import Taxonomy, fetch_taxonomy
from robotoff.types import JSONType

from .text_utils import fold, get_tag

NUTRIMENT_NAMES = (
    "fat",
    "saturated_fat",
    "carbohydrates",
    "sugars",
    "fiber",
    "proteins",
    "salt",
    "energy_kcal",
    "fruits_vegetables_nuts",
)


@cachetools.cached(cachetools.LRUCache(maxsize=1))
def get_ingredient_taxonomy():
    return fetch_taxonomy(
        "", Path(__file__).parent / "ingredients.full.json.gz", offline=True
    )


@cachetools.cached(cachetools.LRUCache(maxsize=1))
def get_ingredient_processor():
    ingredient_taxonomy = get_ingredient_taxonomy()
    return build_ingredient_processor(
        ingredient_taxonomy, add_synonym_combinations=True
    )


def generate_inputs_from_product(product: JSONType, ocr_texts: list[str]) -> JSONType:
    """Generate inputs for v3 category predictor model.

    :param product: the product dict, the `product_name` and `ingredients`
        fields are used, if provided
    :param ocr_texts: a list of detected OCR texts, one per image
    :return: a dict containing inputs for v3 category predictor model
    """
    ingredient_taxonomy = get_ingredient_taxonomy()
    ingredient_processor = get_ingredient_processor()

    inputs = {
        "product_name": product.get("product_name", ""),
        "ingredients_tags": transform_ingredients_input(
            product.get("ingredients", []), ingredient_taxonomy
        )
        or [""],
        "ingredients_ocr_tags": extract_ocr_ingredients(
            ocr_texts, processor=ingredient_processor, debug=False
        )
        or [""],
    }

    nutriments = product.get("nutriments", {})
    for nutriment_name in NUTRIMENT_NAMES:
        inputs[nutriment_name] = transform_nutrition_input(
            nutriments.get(f"{nutriment_name.replace('_', '-')}_100g"),
            nutriment_name=nutriment_name,
        )
    return inputs


def remove_untaxonomized_values(value_tags: list[str], taxonomy: Taxonomy) -> list[str]:
    return [value_tag for value_tag in value_tags if value_tag in taxonomy]


def transform_ingredients_input(
    ingredients: list[dict], taxonomy: Taxonomy
) -> list[str]:
    # Only keep nodes of depth=1 (i.e. don't keep sub-ingredients)
    # While sub-ingredients may be interesting for classification, enough signal is already
    # should already be present in the main ingredient, and it makes it more difficult to
    # take ingredient order into account (as we don't know if sub-ingredient #2 of
    # ingredient #1 is more present than sub-ingredient #1 of ingredient #2)
    return remove_untaxonomized_values(
        [get_tag(ingredient["id"]) for ingredient in ingredients], taxonomy
    )


def transform_nutrition_input(value: Optional[float], nutriment_name: str) -> float:
    """Transform nutritional values before model inference.

    This function returns:

    - -1, if the value is missing
    - -2, if the value is obviously or suspiciously wrong (<0 or >=101 for all
        nutriments except energy, <0 or >=3800 kcal for energy)
    - the input value otherwise

    :param value: the float value
    :param nutriment_name: the name of the nutriment
    :return: the transformed nutriment value
    """
    if value is None:
        return -1

    if nutriment_name == "energy-kcal":
        if value >= 3800 or value < 0:
            # Too high to be true
            return -2

    elif value < 0 or value >= 101:
        # Remove invalid values
        return -2

    return value


MULTIPLE_SPACES_REGEX = re.compile(r" {2,}")


def extract_ocr_ingredients(
    values: list[str], processor: KeywordProcessor, debug: bool = False
) -> list[str]:
    """Extract ingredient tags from OCR texts.

    :param values: a list of OCR texts, one string per image
    :param processor: the ingredient KeywordProcessor, see
        `build_ingredient_processor`
    :param debug: if True return `{INGREDIENT_TAG}|{LANG}` as output instead
        of only `{INGREDIENT_TAG}`, defaults to False
    :return: the list of detected ingredient tags
    """
    texts = []
    for ocr_data in values:
        text = ocr_data.replace("\n", " ")
        text = MULTIPLE_SPACES_REGEX.sub(" ", text)
        texts.append(text)

    full_text = "|".join(texts)
    matches = []
    for keys, _, __ in extract_ingredient_from_text(processor, full_text):
        match = (
            [f"{node_id}|{lang}" for (node_id, lang) in keys]
            if debug
            else [node_id for (node_id, _) in keys]
        )
        matches += match
    return sorted(set(matches), key=matches.index)


INGREDIENT_ID_EXCLUDE_LIST = {
    "en:n",
    "en:no1",
    "en:no2",
    "en:no3",
    "en:no4",
    "en:no5",
    "en:no6",
    "en:no7",
    "en:no8",
    "en:no9",
    "en:no10",
    "en:no11",
    "en:no12",
}


def build_ingredient_processor(
    ingredient_taxonomy: Taxonomy, add_synonym_combinations: bool = True
) -> KeywordProcessor:
    """Create a flashtext KeywordProcessor from an ingredient taxonomy.

    :param ingredient_taxonomy: the ingredient taxonomy
    :param add_synonym_combinations: if True, add all multi-words combinations
        using ingredient synonyms, defaults to True.
        Example: if ingredient 'apple' has 'apples' as a synonym and 'juice'
        has 'juices', 'apples juice', 'apples juices', and 'apple juices' will
        be added as patterns to detect ingredient 'apple juice'.
    :return: a KeywordProcessor
    """
    # dict mapping an normalized ingredient to a set of (node ID, lang) tuples
    name_map = defaultdict(set)
    # it's the reverse structure as name_map, dict mapping a (node ID, lang)
    # to a set of normalized names. Used to generate synonym combinations
    synonyms = defaultdict(set)
    for node in ingredient_taxonomy.iter_nodes():
        if node.id in INGREDIENT_ID_EXCLUDE_LIST:
            # Ignore ingredients that create false positive
            continue
        # dict mapping lang to a set of expressions for a specific ingredient
        seen: dict[str, set[str]] = defaultdict(set)
        for field in ("names", "synonyms"):
            for lang in ("xx", "en", "fr", "en", "es", "de", "nl", "it"):
                names = getattr(node, field).get(lang)
                if names is None:
                    continue
                if isinstance(names, str):
                    # for 'names' field, the value is a string
                    names = [names]

                for name in names:
                    normalized_name = fold(name.lower())
                    if normalized_name in seen[lang] or len(normalized_name) <= 1:
                        # Don't keep the normalized name if it already exists
                        # or if it's length is <= 1 (to avoid false positives)
                        # For example 'd' is a synonym for 'vitamin d'
                        continue
                    synonyms[(node.id, lang)].add(normalized_name)
                    name_map[normalized_name].add((node.id, lang))
                    seen[lang].add(normalized_name)

    if add_synonym_combinations:
        for normalized_name, keys in list(name_map.items()):
            # get tokens from name by performing a simple whitespace
            # tokenization
            tokens = normalized_name.split(" ")
            if len(tokens) <= 1:
                continue

            for current_node_id, current_lang in keys:
                # combinations is a list of set of string, each element being
                # a token with multiple possible synonyms.
                # we initialize with the original tokens (if no synonym is
                # found for any token, we will just generate the original
                # normalized name again)
                combinations = [{token} for token in tokens]
                for token_idx in range(len(tokens)):
                    token = tokens[token_idx]
                    if token in name_map:
                        # Lookup all ingredient IDs with the same lang that
                        # match the normalized token string
                        for key in (
                            (node_id, lang)
                            for (node_id, lang) in name_map[token]
                            if lang == current_lang
                        ):
                            for synonym in synonyms[key]:
                                combinations[token_idx].add(synonym)

                for combination in itertools.product(*combinations):
                    # generate full ingredient name using one of the combinations
                    name = " ".join(combination)
                    # As name_map values are sets, we're sure there are no
                    # duplicates
                    name_map[name].add((current_node_id, current_lang))

    processor = KeywordProcessor()
    for pattern, keys in name_map.items():
        processor.add_keyword(pattern, list(keys))
    return processor


FORBIDDEN_CHARS = set(string.ascii_lowercase + string.digits)


def extract_ingredient_from_text(
    processor: KeywordProcessor, text: str
) -> list[tuple[list[tuple[str, str]], int, int]]:
    """Extract taxonomy ingredients from text.

    :param processor: the flashtext processor created with
        `build_ingredient_processor`
    :param text: the text to extract ingredients from
    :return: a list of (keys, start_idx, end_idx) tuples, where keys is a list
        of (node ID, lang) tuples
    """
    text = fold(text.lower())
    return processor.extract_keywords(text, span_info=True)
