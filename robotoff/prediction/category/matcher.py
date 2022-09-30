import datetime
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

import cachetools
from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.products import ProductDataset
from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.utils import dump_json, get_logger, load_json
from robotoff.utils.text import (
    get_lemmatizing_nlp,
    strip_accents_ascii,
    strip_consecutive_spaces,
)

logger = get_logger(__name__)

SUPPORTED_LANG = {"fr", "en", "de", "es", "it", "nl"}

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

STOP_WORDS_EXCEPTIONS = {
    "fr": {"deux", "trois", "quatre"},
    "en": {"two", "three", "four"},
    "es": {"dos", "tres", "cuatro"},
}


MATCH_MAPS_EXCEPTIONS = {
    TaxonomyType.category.name: {
        "fr": {
            # "pas de gluten" becomes "gluten" after lemmatization
            "gluten",
            # "charolais" is a cheese name but is much more commonly used for
            # beef
            "charolais",
            # "frais" implies "en:fresh-food", but as we currently discard
            # predictions if two matches occurs with the same product name,
            # it's better to ignore this
            "frais",
            # "premier cru" becomes "cru" after lemmatization
            "cru",
        }
    }
}


def preprocess_product_name(name: str, lang: str) -> str:
    """Preprocess product name before matching:
    - remove all weight mentions (100 g, 1l,...)
    - remove all label mentions (IGP, AOP, Label Rouge,...)
    - remove uninformative words that lower recall

    :param name: the product name
    :param lang: the language of the product name
    :return: the preprocessed product name
    """
    name = name.lower()
    name = WEIGHT_REGEX.sub("", name)  # Remove weights

    if lang in LABELS_REGEX:
        # Remove labels
        name = LABELS_REGEX[lang].sub("", name)

    if lang in EXTRAWORDS_REGEX:
        # Remove marketing words
        name = EXTRAWORDS_REGEX[lang].sub("", name)

    name = strip_consecutive_spaces(name)
    name = name.strip()
    return name


def process(text: str, lang: str) -> str:
    """Text processing pipeline for category matching.

    Both category names from the taxonomy and product names should be
    processed with this function before matching. The following steps are
    performed:
    - lowercasing
    - language-specific stop word removal
    - language-specific lookup-based lemmatization: fast and independent of
    part of speech for speed and simplicity
    - NFKD unicode normalization and accent stripping

    :param text: text to process
    :param lang: language of the text
    :return: the processed string
    """
    nlp = get_lemmatizing_nlp(lang)
    lemmas = []

    # Savigny-lès-Beaune -> Savigny lès Beaune
    text = text.lower().replace("-", " ")
    doc = nlp(text)
    lang_stop_words_exceptions = STOP_WORDS_EXCEPTIONS.get(lang, set())

    for token in doc:
        if (
            (token.is_stop and token.orth_ not in lang_stop_words_exceptions)
            or token.is_punct
            or token.is_space
        ):
            continue
        lemmas.append(token.lemma_)

    return strip_accents_ascii(" ".join(lemmas))


def generate_match_maps(
    taxonomy_type: str,
) -> Dict[str, Dict[str, List[Tuple[str, str]]]]:
    """Return a dict mapping each supported lang to a match map dict.

    Each match map dict maps a processed string to a list of
    (value_tag, original_name) tuples. Queries are processed through
    the `process` function. We have a match if the processed query is a key of
    the map. It provides a very fast (although not memory-efficient) way of
    performing matching.

    :param taxonomy_type: the taxonomy to build the match maps from
    :return: the match maps
    """
    taxonomy = get_taxonomy(taxonomy_type)
    store: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
    for node in taxonomy.iter_nodes():
        for lang in set(node.names) | set(node.synonyms):
            if lang not in SUPPORTED_LANG:
                continue
            store.setdefault(lang, {})

            names = []
            if lang in node.names:
                names.append(node.names[lang])
            names += node.synonyms.get(lang, [])
            match_exceptions = MATCH_MAPS_EXCEPTIONS.get(taxonomy_type, {}).get(
                lang, set()
            )
            for name in names:
                processed = process(name, lang)
                # Don't add it to the store if empty or if it's in the
                # exception list
                if processed and processed not in match_exceptions:
                    if processed not in store[lang]:
                        store[lang][processed] = []
                    if node.id not in (item[0] for item in store[lang][processed]):
                        store[lang][processed].append((node.id, name))

    return store


@cachetools.cached(cache=cachetools.Cache(maxsize=2))
def get_match_maps(taxonomy_type: str):
    """Return match maps saved on-disk for supported language.

    See `generate_match_maps` function for more information.
    """
    return load_json(
        settings.CATEGORY_MATCHER_MATCH_MAPS[taxonomy_type], compressed=True
    )


@cachetools.cached(cache=cachetools.TTLCache(maxsize=1, ttl=3600))
def get_processors() -> Dict[str, KeywordProcessor]:
    """Return a dict mapping lang to KeywordProcessor used to perform category
    matching."""
    match_maps = get_match_maps(TaxonomyType.category.name)
    processors = {}
    for lang, items in match_maps.items():
        processor = KeywordProcessor()
        for pattern, results in items.items():
            processor.add_keyword(
                pattern,
                [(id_, pattern, category_name) for id_, category_name in results],
            )
        processors[lang] = processor
    return processors


def generate_intersect_categories_ingredients() -> Dict[str, Set[str]]:
    """Return all taxonomized values that are present both in the ingredient
    and in the category taxonomy.

    We use match maps from both taxonomies to find names/synonyms that are the
    same in both taxonomies.
    This function is useful to spot categories that are also ingredients.
    """
    ingredient_match_maps = get_match_maps(TaxonomyType.ingredient.name)
    category_match_maps = get_match_maps(TaxonomyType.category.name)
    matches: Dict[str, Set[str]] = {}
    for lang in SUPPORTED_LANG:
        matches[lang] = set()

    for lang in set(ingredient_match_maps) | set(category_match_maps):
        for key in set(ingredient_match_maps[lang]) & set(category_match_maps[lang]):
            for item in category_match_maps[lang][key]:
                matches[lang].add(item[0])  # Add node ID

    return matches


@cachetools.cached(cache=cachetools.Cache(maxsize=1))
def get_intersect_categories_ingredients():
    """Return intersection between category and ingredient maps saved on-disk
    for supported language.

    See `generate_intersect_categories_ingredients` function for more
    information.
    """
    return {
        k: set(v)
        for k, v in load_json(
            settings.CATEGORY_MATCHER_INTERSECT, compressed=True
        ).items()
    }


def match(query: str, lang: str) -> List[Tuple[str, str, str, str, Tuple[int, int]]]:
    """Perform category matching.

    If a match is also an ingredient (see
    `generate_intersect_categories_ingredients`), we only keep the match if
    it starts at the beginning of the query. It prevents many over-matchings
    with ingredient names in the query that are not the product category.

    :param query: the unprocessed category name
    :param lang: the language of the query
    :return A list of matches (category_value_tag, matched_pattern)
    """
    processors = get_processors()
    if lang not in processors:
        return []

    processor = processors[lang]
    query = preprocess_product_name(query, lang)
    query = process(query, lang)
    flat_results = []
    for results, start_idx, end_idx in processor.extract_keywords(
        query, span_info=True
    ):
        for result in results:
            flat_results.append((result, start_idx, end_idx))
    filtered = []
    category_ingredient_intersect = get_intersect_categories_ingredients()[lang]
    for (id_, pattern, category_name), start_idx, end_idx in flat_results:
        # If the category is also an ingredient, we require the match
        # to start at the beginning of the query
        # This prevent for instance "pineapple" category to match
        # "pizza with pineapple" product name
        if id_ in category_ingredient_intersect and start_idx != 0:
            continue
        filtered.append((id_, category_name, pattern, query, (start_idx, end_idx)))
    return filtered


def predict_by_lang(product: Dict) -> Dict[str, List[Prediction]]:
    """Predict product categories using a matching algorithm on product names
    for all supported languages.

    :param product: product properties
    :return: a dict mapping for each supported lang a list of detected
    category Prediction
    """
    predictions: Dict[str, List[Prediction]] = {}
    for lang in set(product.get("languages_codes", [])) & SUPPORTED_LANG:
        product_name = product.get(f"product_name_{lang}")

        if not product_name:
            continue

        matches = match(product_name, lang)

        predictions[lang] = [
            Prediction(
                type=PredictionType.category,
                barcode=product["code"],
                value_tag=match[0],
                data={
                    "lang": lang,
                    "product_name": product_name,
                    "category_name": match[1],
                    "pattern": match[2],
                    "processed_product_name": match[3],
                    "start_idx": match[4][0],
                    "end_idx": match[4][1],
                    "is_full_match": (match[4][1] - match[4][0] == len(match[3])),
                },
                automatic_processing=False,
                predictor="matcher",
            )
            for match in matches
        ]
    return predictions


def predict(product: Dict) -> List[Prediction]:
    """Predict product categories using a matching algorithm on product names.

    Flashtext always return the longuest match if several patterns match
    the query. Therefore, if more than one category is predicted, it means
    there was two non-overlapping matches: we don't return any prediction for
    that lang in that case.

    :param product: product properties
    :return: a list of category Prediction"""
    predictions_by_lang = predict_by_lang(product)
    predictions = []
    for _, lang_predictions in predictions_by_lang.items():
        if len(lang_predictions) != 1:
            # if there is more than one match, matches on this product name
            # are ambiguous and we discard them
            continue

        predictions += lang_predictions

    return predictions


def predict_from_dataset(
    dataset: ProductDataset, from_datetime: Optional[datetime.datetime] = None
) -> Iterable[Prediction]:
    """Return an iterable of category predictions, using the provided dataset.

    Args:
        dataset: a ProductDataset
        from_datetime: datetime threshold: only keep products modified after
            `from_datetime`
    """
    product_stream = (
        dataset.stream()
        .filter_nonempty_text_field("code")
        .filter_nonempty_text_field("product_name")
        .filter_empty_tag_field("categories_tags")
        .filter_nonempty_tag_field("countries_tags")
        .filter_nonempty_tag_field("languages_codes")
    )

    if from_datetime:
        product_stream = product_stream.filter_by_modified_datetime(
            from_t=from_datetime
        )

    logger.info("Performing prediction on products without categories")
    for product in product_stream.iter():
        yield from predict(product)


def dump_resource_files():
    """Generate and save on-disk match maps (ingredient and category) and the
    category-ingredient intersection."""
    for taxonomy_type in (TaxonomyType.ingredient.name, TaxonomyType.category.name):
        match_map = generate_match_maps(taxonomy_type)
        dump_json(
            settings.CATEGORY_MATCHER_MATCH_MAPS[taxonomy_type],
            match_map,
            compressed=True,
        )

    intersect = generate_intersect_categories_ingredients()
    dump_json(
        settings.CATEGORY_MATCHER_INTERSECT,
        {k: list(v) for k, v in intersect.items()},
        compressed=True,
    )
