import collections
import logging

from cachetools.func import ttl_cache
from openfoodfacts.taxonomy import (
    Taxonomy,
    create_brand_taxonomy_mapping,
    create_taxonomy_mapping,
)
from openfoodfacts.taxonomy import get_taxonomy as _get_taxonomy
from openfoodfacts.types import TaxonomyType

from robotoff import settings
from robotoff.utils.cache import function_cache_register

logger = logging.getLogger(__name__)


def generate_category_hierarchy(
    taxonomy: Taxonomy, category_to_index: dict[str, int], root: int
):
    categories_hierarchy: dict[int, set] = collections.defaultdict(set)

    for node in taxonomy.iter_nodes():
        category_index = category_to_index[node.id]

        if not node.parents:
            categories_hierarchy[root].add(category_index)

        children_indexes = {
            category_to_index[c.id] for c in node.children if c.id in category_to_index
        }

        categories_hierarchy[category_index] = categories_hierarchy[
            category_index
        ].union(children_indexes)

    categories_hierarchy_list = {}
    for category in categories_hierarchy.keys():
        categories_hierarchy_list[category] = list(categories_hierarchy[category])

    return categories_hierarchy_list


# ttl: 12h
@ttl_cache(maxsize=100, ttl=12 * 60 * 60)
def get_taxonomy(taxonomy_type: TaxonomyType | str, offline: bool = False) -> Taxonomy:
    """Return the taxonomy of type `taxonomy_type`.

    The taxonomy is cached in memory and locally on disk. Every 12h, we check
    if a new version is available and download if True.

    A local static version can also be fetched (for unit tests for example)
    with `offline=True`.

    :param taxonomy_type: the taxonomy type
    :param offline: if True, return a local static version of the taxonomy,
      defaults to False. It's not available for all taxonomy types.
    :return: the Taxonomy
    """
    taxonomy_offline_path = str(settings.TAXONOMY_PATHS[taxonomy_type])
    cache_dir = settings.DATA_DIR / "taxonomies"
    if offline:
        return Taxonomy.from_path(taxonomy_offline_path)

    taxonomy_type_enum = (
        TaxonomyType[taxonomy_type] if isinstance(taxonomy_type, str) else taxonomy_type
    )

    try:
        return _get_taxonomy(
            taxonomy_type_enum,
            force_download=False,
            download_newer=True,
            cache_dir=cache_dir,
        )
    except Exception as e:
        logger.error(
            "Error while fetching taxonomy %s: %s.",
            taxonomy_type,
            e,
        )

    try:
        logger.info("Trying to load taxonomy %s from local cache...", taxonomy_type)
        return _get_taxonomy(
            taxonomy_type_enum,
            force_download=False,
            download_newer=False,
            cache_dir=cache_dir,
        )
    except Exception as e:
        logger.info(
            "No cached version of taxonomy %s found or error while loading it: %s. ",
            taxonomy_type,
            e,
        )

    logger.info(
        "Loading taxonomy %s from local static file %s...",
        taxonomy_type,
        taxonomy_offline_path,
    )
    return Taxonomy.from_path(taxonomy_offline_path)


def is_prefixed_value(value: str) -> bool:
    """Return True if the given value has a language prefix (en:, fr:,...),
    False otherwise."""
    return len(value) > 3 and value[2] == ":"


# ttl: 12h
@ttl_cache(maxsize=2, ttl=12 * 60 * 60)
def get_taxonomy_mapping(taxonomy_type: str) -> dict[str, str]:
    """Return for label type a mapping of prefixed taxonomy values in all
    languages (such as `fr:bio-europeen` or `es:"ecologico-ue`) to their
    canonical value (`en:organic` for the previous example).
    """
    logger.debug("Loading taxonomy mapping %s...", taxonomy_type)
    taxonomy = get_taxonomy(taxonomy_type)

    if taxonomy_type == TaxonomyType.brand.name:
        return create_brand_taxonomy_mapping(taxonomy)
    else:
        return create_taxonomy_mapping(taxonomy)


def match_taxonomized_value(value_tag: str, taxonomy_type: str) -> str | None:
    """Return the canonical taxonomized value of a `value_tag` (if any) or
    return None if no match was found or if the type is unsupported.

    Currently it only works for brand, label and category taxonomies.
    """
    if taxonomy_type not in (
        TaxonomyType.brand.name,
        TaxonomyType.label.name,
        TaxonomyType.category.name,
    ):
        return None

    taxonomy = get_taxonomy(taxonomy_type)

    if value_tag in taxonomy:
        return value_tag

    return get_taxonomy_mapping(taxonomy_type).get(value_tag)


def load_resources():
    """Load and cache resources."""
    for taxonomy_type in settings.TAXONOMY_URLS:
        get_taxonomy(taxonomy_type)

    for taxonomy_type in (TaxonomyType.brand, TaxonomyType.label):
        get_taxonomy_mapping(taxonomy_type.name)


function_cache_register.register(get_taxonomy)
function_cache_register.register(get_taxonomy_mapping)
