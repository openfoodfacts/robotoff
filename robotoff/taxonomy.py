import collections
import functools
import pathlib
from enum import Enum
from typing import Dict, Iterable, List, Optional, Set, Union

import orjson

from robotoff import settings
from robotoff.utils import get_logger, http_session
from robotoff.utils.cache import CachedStore
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
    __slots__ = ("id", "names", "parents", "children", "synonyms")

    def __init__(
        self,
        identifier: str,
        names: Dict[str, str],
        synonyms: Optional[Dict[str, List[str]]],
    ):
        self.id: str = identifier
        self.names: Dict[str, str] = names
        self.parents: List["TaxonomyNode"] = []
        self.children: List["TaxonomyNode"] = []

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
                )
                taxonomy.add(key, node)

        for key, key_data in data.items():
            node = taxonomy[key]
            parents = [taxonomy[ref] for ref in key_data.get("parents", [])]
            node.add_parents(parents)

        return taxonomy

    @classmethod
    def from_json(cls, file_path: Union[str, pathlib.Path]):
        with open(str(file_path), "rb") as f:
            data = orjson.loads(f.read())
            return cls.from_dict(data)

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


def fetch_taxonomy(url: str, fallback_path: str, offline=False) -> Optional[Taxonomy]:
    if offline:
        return Taxonomy.from_json(fallback_path)

    try:
        r = http_session.get(url, timeout=5)
        data = r.json()
    except Exception:
        logger.warning("Timeout while fetching '{}' taxonomy".format(url))
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
        )
    ),
    TaxonomyType.ingredient.name: CachedStore(
        functools.partial(
            fetch_taxonomy,
            url=settings.TAXONOMY_INGREDIENT_URL,
            fallback_path=settings.TAXONOMY_INGREDIENT_PATH,
        )
    ),
    TaxonomyType.label.name: CachedStore(
        functools.partial(
            fetch_taxonomy,
            url=settings.TAXONOMY_LABEL_URL,
            fallback_path=settings.TAXONOMY_LABEL_PATH,
        )
    ),
    TaxonomyType.brand.name: CachedStore(
        functools.partial(
            fetch_taxonomy,
            url=settings.TAXONOMY_BRAND_URL,
            fallback_path=settings.TAXONOMY_LABEL_PATH,
        )
    ),
}


def get_taxonomy(taxonomy_type: str) -> Taxonomy:
    """Returned the requested Taxonomy."""
    taxonomy_store = TAXONOMY_STORES.get(taxonomy_type)

    if taxonomy_store is None:
        raise ValueError("unknown taxonomy type: {}".format(taxonomy_type))

    return taxonomy_store.get()


def get_unprefixed_mapping(taxonomy_type: str) -> Dict[str, str]:
    taxonomy = get_taxonomy(taxonomy_type)
    ids: Dict[str, str] = {}

    for key in taxonomy.keys():
        unprefixed_key = key
        if len(key) > 3 and key[2] == ":":
            unprefixed_key = key[3:]

        if taxonomy_type == TaxonomyType.brand.name:
            ids[unprefixed_key] = taxonomy[key].names["en"]
        else:
            ids[unprefixed_key] = key

    return ids


UNPREFIXED_MAPPING_STORE: Dict[str, CachedStore] = {
    TaxonomyType.label.name: CachedStore(
        functools.partial(
            get_unprefixed_mapping,
            taxonomy_type=TaxonomyType.label.name,
        )
    ),
    TaxonomyType.brand.name: CachedStore(
        functools.partial(
            get_unprefixed_mapping,
            taxonomy_type=TaxonomyType.brand.name,
        )
    ),
}


def match_unprefixed_value(value_tag: str, taxonomy_type: str) -> Optional[str]:
    unprefixed_mapping_cache = UNPREFIXED_MAPPING_STORE.get(taxonomy_type)

    if unprefixed_mapping_cache is None:
        return None

    unprefixed_mapping = unprefixed_mapping_cache.get()
    return unprefixed_mapping.get(value_tag)
