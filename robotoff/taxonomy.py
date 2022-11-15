import collections
import functools
import pathlib
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set, Union

import cachetools
import requests

from robotoff import settings
from robotoff.utils import get_logger, http_session, load_json
from robotoff.utils.cache import CachedStore
from robotoff.utils.text import get_tag
from robotoff.utils.types import JSONType

try:
    import networkx
except ImportError:
    networkx = None

logger = get_logger(__name__)


class TaxonomyType(Enum):
    category = 1
    ingredient = 2
    label = 3
    brand = 4


class TaxonomyNode:
    __slots__ = ("id", "names", "parents", "children", "synonyms", "additional_data")

    def __init__(
        self,
        identifier: str,
        names: Dict[str, str],
        synonyms: Optional[Dict[str, List[str]]],
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        self.id: str = identifier
        self.names: Dict[str, str] = names
        self.parents: List["TaxonomyNode"] = []
        self.children: List["TaxonomyNode"] = []
        self.additional_data = additional_data or {}

        if synonyms:
            self.synonyms = synonyms
        else:
            self.synonyms = {}

    def is_child_of(self, item: "TaxonomyNode") -> bool:
        """Return True if `item` is a child of `self` in the taxonomy."""
        if not self.parents:
            return False

        if item in self.parents:
            return True

        for parent in self.parents:
            is_parent = parent.is_child_of(item)

            if is_parent:
                return True

        return False

    def is_parent_of(self, item: "TaxonomyNode") -> bool:
        return item.is_child_of(self)

    def is_parent_of_any(self, candidates: Iterable["TaxonomyNode"]) -> bool:
        for candidate in candidates:
            if candidate.is_child_of(self):
                return True

        return False

    def get_parents_hierarchy(self) -> List["TaxonomyNode"]:
        """Return the list of all parent nodes (direct and indirect)."""
        all_parents = []
        seen: Set[str] = set()

        if not self.parents:
            return []

        for self_parent in self.parents:
            if self_parent.id not in seen:
                all_parents.append(self_parent)
                seen.add(self_parent.id)

            for parent_parent in self_parent.get_parents_hierarchy():
                if parent_parent.id not in seen:
                    all_parents.append(parent_parent)
                    seen.add(parent_parent.id)

        return all_parents

    def get_localized_name(self, lang: str) -> str:
        if lang in self.names:
            return self.names[lang]

        return self.id

    def get_synonyms(self, lang: str) -> List[str]:
        return self.synonyms.get(lang, [])

    def add_parents(self, parents: Iterable["TaxonomyNode"]):
        for parent in parents:
            if parent not in self.parents:
                self.parents.append(parent)
                parent.children.append(self)

    def to_dict(self) -> JSONType:
        return {"name": self.names, "parents": [p.id for p in self.parents]}

    def __repr__(self):
        return "<TaxonomyNode %s>" % self.id


class Taxonomy:
    def __init__(self):
        self.nodes: Dict[str, TaxonomyNode] = {}

    def add(self, key: str, node: TaxonomyNode) -> None:
        self.nodes[key] = node

    def __contains__(self, item: str):
        return item in self.nodes

    def __getitem__(self, item: str):
        return self.nodes.get(item)

    def __len__(self):
        return len(self.nodes)

    def iter_nodes(self) -> Iterable[TaxonomyNode]:
        """Iterate over the nodes of the taxonomy."""
        return iter(self.nodes.values())

    def keys(self):
        return self.nodes.keys()

    def find_deepest_nodes(self, nodes: List[TaxonomyNode]) -> List[TaxonomyNode]:
        """Given a list of nodes, returns the list of nodes where all the parents
        within the list have been removed.

        For example, for a taxonomy, 'fish' -> 'salmon' -> 'smoked-salmon':

        ['fish', 'salmon'] -> ['salmon']
        ['fish', 'smoked-salmon'] -> [smoked-salmon']
        """
        excluded: Set[str] = set()

        for node in nodes:
            for second_node in (
                n for n in nodes if n.id not in excluded and n.id != node.id
            ):
                if node.is_child_of(second_node):
                    excluded.add(second_node.id)

        return [node for node in nodes if node.id not in excluded]

    def is_parent_of_any(
        self, item: str, candidates: Iterable[str], raises: bool = True
    ) -> bool:
        """Return True if `item` is parent of any candidate, False otherwise.

        If the item is not in the taxonomy and raises is False, return False.

        :param item: The item to compare
        :param candidates: A list of candidates
        :param raises: if True, raises a ValueError if item is not in the
        taxonomy, defaults to True.
        """
        node: TaxonomyNode = self[item]

        if node is None:
            if raises:
                raise ValueError(f"unknown id in taxonomy: {node}")
            else:
                return False

        to_check_nodes: Set[TaxonomyNode] = set()

        for candidate in candidates:
            candidate_node = self[candidate]

            if candidate_node is not None:
                to_check_nodes.add(candidate_node)

        return node.is_parent_of_any(to_check_nodes)

    def get_localized_name(self, key: str, lang: str) -> str:
        if key not in self.nodes:
            return key

        return self.nodes[key].get_localized_name(lang)

    def to_dict(self) -> JSONType:
        export = {}

        for key, node in self.nodes.items():
            export[key] = node.to_dict()

        return export

    @classmethod
    def from_dict(cls, data: JSONType) -> "Taxonomy":
        taxonomy = Taxonomy()

        for key, key_data in data.items():
            if key not in taxonomy:
                node = TaxonomyNode(
                    identifier=key,
                    names=key_data.get("name", {}),
                    synonyms=key_data.get("synonyms", None),
                    additional_data={
                        k: v
                        for k, v in key_data.items()
                        if k not in {"parents", "name", "synonyms", "children"}
                    },
                )
                taxonomy.add(key, node)

        for key, key_data in data.items():
            node = taxonomy[key]
            parents = [taxonomy[ref] for ref in key_data.get("parents", [])]
            node.add_parents(parents)

        return taxonomy

    @classmethod
    def from_json(cls, file_path: Union[str, pathlib.Path]):
        return cls.from_dict(load_json(file_path, compressed=True))  # type: ignore

    def to_graph(self):
        """Generate a networkx.DiGraph from the taxonomy."""
        graph = networkx.DiGraph()
        graph.add_nodes_from((x.id for x in self.iter_nodes()))

        for node in self.iter_nodes():
            for child in node.children:
                graph.add_edge(node.id, child.id)

        return graph


def generate_category_hierarchy(
    taxonomy: Taxonomy, category_to_index: Dict[str, int], root: int
):
    categories_hierarchy: Dict[int, Set] = collections.defaultdict(set)

    for node in taxonomy.iter_nodes():
        category_index = category_to_index[node.id]

        if not node.parents:
            categories_hierarchy[root].add(category_index)

        children_indexes = set(
            [
                category_to_index[c.id]
                for c in node.children
                if c.id in category_to_index
            ]
        )

        categories_hierarchy[category_index] = categories_hierarchy[
            category_index
        ].union(children_indexes)

    categories_hierarchy_list = {}
    for category in categories_hierarchy.keys():
        categories_hierarchy_list[category] = list(categories_hierarchy[category])

    return categories_hierarchy_list


def fetch_taxonomy(
    url: str, fallback_path: str, offline: bool = False
) -> Optional[Taxonomy]:
    if offline:
        return Taxonomy.from_json(fallback_path)

    try:
        r = http_session.get(url, timeout=120)  # might take some time
        if r.status_code >= 300:
            raise requests.HTTPError(
                "Taxonomy download at %s returned status code {r.status_code}", url
            )
        data = r.json()
    except Exception as e:
        logger.exception(f"{type(e)} exception while fetching taxonomy at %s", url)
        if fallback_path:
            return Taxonomy.from_json(fallback_path)
        else:
            return None

    return Taxonomy.from_dict(data)


TAXONOMY_STORES: Dict[str, CachedStore] = {
    TaxonomyType.category.name: CachedStore(
        functools.partial(
            fetch_taxonomy,
            url=settings.TAXONOMY_CATEGORY_URL,
            fallback_path=settings.TAXONOMY_CATEGORY_PATH,
        ),
        expiration_interval=720,
    ),
    TaxonomyType.ingredient.name: CachedStore(
        functools.partial(
            fetch_taxonomy,
            url=settings.TAXONOMY_INGREDIENT_URL,
            fallback_path=settings.TAXONOMY_INGREDIENT_PATH,
        ),
        expiration_interval=720,
    ),
    TaxonomyType.label.name: CachedStore(
        functools.partial(
            fetch_taxonomy,
            url=settings.TAXONOMY_LABEL_URL,
            fallback_path=settings.TAXONOMY_LABEL_PATH,
        ),
        expiration_interval=720,
    ),
    TaxonomyType.brand.name: CachedStore(
        functools.partial(
            fetch_taxonomy,
            url=settings.TAXONOMY_BRAND_URL,
            fallback_path=settings.TAXONOMY_BRAND_PATH,
        ),
        expiration_interval=720,
    ),
}


def get_taxonomy(taxonomy_type: str, offline: bool = False) -> Taxonomy:
    """Returned the requested Taxonomy."""
    taxonomy_store = TAXONOMY_STORES.get(taxonomy_type)

    if taxonomy_store is None:
        raise ValueError("unknown taxonomy type: {}".format(taxonomy_type))

    return taxonomy_store.get(offline=offline)


def is_prefixed_value(value: str) -> bool:
    """Return True if the given value has a language prefix (en:, fr:,...),
    False otherwise."""
    return len(value) > 3 and value[2] == ":"


@cachetools.cached(cachetools.TTLCache(maxsize=2, ttl=43200))  # 12h TTL
def get_taxonomy_mapping(taxonomy_type: str) -> Dict[str, str]:
    """Return for label type a mapping of prefixed taxonomy values in all
    languages (such as `fr:bio-europeen` or `es:"ecologico-ue`) to their
    canonical value (`en:organic` for the previous example).
    """
    taxonomy = get_taxonomy(taxonomy_type)
    ids: Dict[str, str] = {}

    for key in taxonomy.keys():
        if taxonomy_type == TaxonomyType.brand.name:
            unprefixed_key = key
            if is_prefixed_value(key):
                unprefixed_key = key[3:]
            ids[unprefixed_key] = taxonomy[key].names["en"]
        else:
            for lang, name in taxonomy[key].names.items():
                tag = get_tag(name)
                ids[f"{lang}:{tag}"] = key

    return ids


def match_taxonomized_value(value_tag: str, taxonomy_type: str) -> Optional[str]:
    """Return the canonical taxonomized value of a `value_tag` (if any) or
    return None if no match was found or if the type is unsupported.

    Currently it only works for brand and label.
    """
    if taxonomy_type not in (TaxonomyType.brand.name, TaxonomyType.label.name):
        return None

    taxonomy = get_taxonomy(taxonomy_type)

    if value_tag in taxonomy:
        return value_tag

    return get_taxonomy_mapping(taxonomy_type).get(value_tag)
