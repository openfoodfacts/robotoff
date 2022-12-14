import datetime
import itertools
import operator
import re
from typing import Iterable, Optional

import cachetools
from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.prediction.types import Prediction
from robotoff.products import ProductDataset
from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.types import PredictionType
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
    "de": {"jahren", "jahr"},
    "it": {"anno"},
}


# During stemming/stop-word removal of category names, sometimes the processed
# string becomes too generic and adds too many false positive detections.
# For instance, in French 'premier cru' is processed into 'cru' (because
# premier is a stop word), which can be found in the names of many products
# that do not belong to the "premier cru" category
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
            # "dès un an" becomes "an" an after lemmatization
            "an",
        },
        "es": {
            # en:fresh-food
            "fresco",
        },
        "en": {
            # en:fresh-food
            "fresh",
        },
        "de": {
            # frish -> frischen after lemmatization (en:fresh-foods)
            "frischen",
        },
    }
}

MatchMapType = dict[str, dict[str, list[tuple[str, str]]]]


def load_resources():
    """Load and cache resources."""
    logger.info("Loading matcher resources...")
    get_processors()
    get_intersect_categories_ingredients()

    for lang in SUPPORTED_LANG:
        logger.info("Loading NLP for %s...", lang)
        get_lemmatizing_nlp(lang)


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
            # skip token as it is uninformative
            continue
        lemmas.append(token.lemma_)

    return strip_accents_ascii(" ".join(lemmas))


def generate_match_maps(taxonomy_type: str) -> MatchMapType:
    """Return a dict mapping each supported lang to a match map dict.

    Each match map dict maps a processed string (the key) to a list of
    (value_tag, original_name) tuples.
    These keys are obtained by using all synonyms and names of `value_tag` in
    different languages and using process function (this may lead to having a
    key corresponding to more than one tag).
    Queries will then be processed through the `process` function. We have a
    match if the processed query is a key of the map.

    It provides a very fast (although not memory-efficient) way of
    performing matching.

    :param taxonomy_type: the taxonomy to build the match maps from
    :return: the match maps
    """
    taxonomy = get_taxonomy(taxonomy_type)
    match_maps_exceptions = MATCH_MAPS_EXCEPTIONS.get(taxonomy_type, {})

    store: MatchMapType = {}
    for node in taxonomy.iter_nodes():
        # node.names is a dict with one expression by language
        # node.synonyms is a dict with a list of expressions by language
        for lang in set(node.names) | set(node.synonyms):
            if lang not in SUPPORTED_LANG:
                continue
            store.setdefault(lang, {})

            names = []
            if lang in node.names:
                names.append(node.names[lang])
            names += node.synonyms.get(lang, [])
            match_exceptions = match_maps_exceptions.get(lang, set())

            # now process harvested names and keep significative ones
            for name in names:
                processed = process(name, lang)
                # Don't add it to the store if empty or if it's in the
                # exception list
                if processed and processed not in match_exceptions:
                    if processed not in store[lang]:
                        store[lang][processed] = []
                    if node.id not in (item[0] for item in store[lang][processed]):
                        store[lang].setdefault(processed, []).append((node.id, name))

    return store


def get_match_maps(taxonomy_type: str) -> MatchMapType:
    """Return match maps saved on-disk for supported language.

    See `generate_match_maps` function for more information.
    """
    return load_json(  # type: ignore
        settings.CATEGORY_MATCHER_MATCH_MAPS[taxonomy_type], compressed=True
    )


@cachetools.cached(cache=cachetools.TTLCache(maxsize=1, ttl=3600))
def get_processors() -> dict[str, KeywordProcessor]:
    """Return a dict mapping lang to flashtext KeywordProcessor used to
    perform category matching.

    This enables a fast matching of query parts against matched maps keys.
    """
    logger.info("Loading category matcher processors...")
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


def generate_intersect_categories_ingredients() -> dict[str, set[str]]:
    """Return all taxonomized values that are present both in the ingredient
    and in the category taxonomy.

    We use match maps from both taxonomies to find names/synonyms that are the
    same in both taxonomies.
    This function is useful to spot categories that are also ingredients.
    """
    ingredient_match_maps = get_match_maps(TaxonomyType.ingredient.name)
    category_match_maps = get_match_maps(TaxonomyType.category.name)
    matches: dict[str, set[str]] = {}
    for lang in SUPPORTED_LANG:
        matches[lang] = set()

    for lang in set(ingredient_match_maps) & set(category_match_maps) & SUPPORTED_LANG:
        for key in set(ingredient_match_maps[lang]) & set(category_match_maps[lang]):
            for node_id, _ in category_match_maps[lang][key]:
                matches[lang].add(node_id)

    return matches


@cachetools.cached(cache=cachetools.Cache(maxsize=1))
def get_intersect_categories_ingredients():
    """Return intersection between category and ingredient maps saved on-disk
    for supported language.

    See `generate_intersect_categories_ingredients` function for more
    information.
    """
    logger.info("Loading category intersection ingredient...")
    return {
        k: set(v)
        for k, v in load_json(
            settings.CATEGORY_MATCHER_INTERSECT, compressed=True
        ).items()
    }


def match(query: str, lang: str) -> list[tuple[str, str, str, str, tuple[int, int]]]:
    """Perform category matching.

    If a match is also an ingredient (see
    `generate_intersect_categories_ingredients`), we only keep the match if
    it starts at the beginning of the query. It prevents many over-matchings
    with ingredient names in the query that are not the product category.

    :param query: the unprocessed product name
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

    # now filter the list to avoid some false positive
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


def predict_by_lang(product: dict) -> dict[str, list[Prediction]]:
    """Predict product categories using a matching algorithm on product names
    for all supported languages.

    :param product: the product to predict the categories from, should have at
    least `product_name_{lang}` and `languages_codes` fields
    :return: a dict mapping for each supported lang a list of detected
    category Prediction
    """
    predictions: dict[str, list[Prediction]] = {}
    for lang in set(product.get("languages_codes", [])) & SUPPORTED_LANG:
        product_name = product.get(f"product_name_{lang}")

        if not product_name:
            continue

        matches = match(product_name, lang)

        predictions[lang] = [
            Prediction(
                type=PredictionType.category,
                value_tag=value_tag,
                data={
                    "lang": lang,
                    "product_name": product_name,
                    "category_name": category_name,
                    "pattern": pattern,
                    "processed_product_name": processed_product_name,
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                    "is_full_match": (
                        end_idx - start_idx == len(processed_product_name)
                    ),
                },
                automatic_processing=False,
                predictor="matcher",
            )
            for (
                value_tag,
                category_name,
                pattern,
                processed_product_name,
                (start_idx, end_idx),
            ) in matches
        ]
    return predictions


def predict(product: dict) -> list[Prediction]:
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
        predictions_by_value_tag = {
            value_tag: list(value_tag_predictions)
            for (value_tag, value_tag_predictions) in itertools.groupby(
                lang_predictions, operator.attrgetter("value_tag")
            )
        }
        if len(predictions_by_value_tag) != 1:
            # if there is more than one match (with different predicted
            # category), matches on this product name are ambiguous and we
            # discard them
            continue

        # all predictions in `lang_predictions` have the same `value_tag`,
        # take the first one
        predictions.append(lang_predictions[0])

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
        for prediction in predict(product):
            prediction.barcode = product["code"]
            yield prediction


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
