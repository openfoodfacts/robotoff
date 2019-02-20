import collections
import functools
import json
from enum import Enum
from typing import List, Dict, Iterable, Optional, Set

import requests

from robotoff import settings
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType


class TaxonomyType(Enum):
    category = 1
    ingredient = 2
    label = 3


class TaxonomyNode:
    __slots__ = ('id', 'names', 'parents', 'children')

    def __init__(self, identifier: str,
                 names: List[Dict[str, str]]):
        self.id: str = identifier
        self.names: Dict[str, str] = names
        self.parents: List['TaxonomyNode'] = []
        self.children: List['TaxonomyNode'] = []

    def is_child_of(self, item: 'TaxonomyNode'):
        return item in self.parents

    def get_localized_name(self, lang: str) -> str:
        if lang in self.names:
            return self.names[lang]

        return self.id

    def add_parents(self, parents: Iterable['TaxonomyNode']):
        for parent in parents:
            if parent not in self.parents:
                self.parents.append(parent)
                parent.children.append(self)

    def to_dict(self) -> JSONType:
        return {
            'name': self.names,
            'parents': [p.id for p in self.parents]
        }

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

    def iter_nodes(self) -> Iterable[TaxonomyNode]:
        return iter(self.nodes.values())

    def keys(self):
        return self.nodes.keys()

    def find_deepest_item(self, keys: List[str]) -> Optional[str]:
        keys = list(set(keys))
        excluded: Set[str] = set()

        if not any(True if key in self.keys() else False for key in keys):
            return None

        keys = [key for key in keys if key in self.keys()]

        if len(keys) == 0:
            return None

        elif len(keys) == 1:
            return keys[0]

        for key in keys:
            for second_item in (i for i in keys if i not in excluded):
                if key == second_item:
                    continue

                if self[key].is_child_of(self[second_item]):
                    excluded.add(second_item)

        return [key for key in keys if key not in excluded][0]

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
    def from_dict(cls, data: JSONType) -> 'Taxonomy':
        taxonomy = Taxonomy()

        for key, key_data in data.items():
            if key not in taxonomy:
                node = TaxonomyNode(identifier=key,
                                    names=key_data.get('name', {}))
                taxonomy.add(key, node)

        for key, key_data in data.items():
            node = taxonomy[key]
            parents = [taxonomy[ref]
                       for ref in key_data.get('parents', [])]
            node.add_parents(parents)

        return taxonomy

    @classmethod
    def from_json(cls, file_path: str):
        with open(file_path, 'r') as f:
            data = json.load(f)
            return cls.from_dict(data)


def generate_category_hierarchy(taxonomy: Taxonomy,
                                category_to_index: Dict[str, int],
                                root: int):
    categories_hierarchy = collections.defaultdict(set)

    for node in taxonomy.iter_nodes():
        category_index = category_to_index[node.id]

        if not node.parents:
            categories_hierarchy[root].add(category_index)

        children_indexes = set([category_to_index[c.id]
                                for c in node.children
                                if c.id in category_to_index])

        categories_hierarchy[category_index] = \
            categories_hierarchy[category_index].union(children_indexes)

    categories_hierarchy_list = {}
    for category in categories_hierarchy.keys():
        categories_hierarchy_list[category] = \
            list(categories_hierarchy[category])

    return categories_hierarchy_list


def fetch_taxonomy(url: str, fallback_path: str, offline=False) \
        -> Optional[Taxonomy]:
    if offline:
        return Taxonomy.from_json(fallback_path)

    try:
        r = requests.get(url)
        data = r.json()
    except Exception:
        if fallback_path:
            return Taxonomy.from_json(fallback_path)
        else:
            return None

    return Taxonomy.from_dict(data)


TAXONOMY_STORES: Dict[str, CachedStore] = {
    TaxonomyType.category.name:
        CachedStore(functools.partial(fetch_taxonomy,
                                      url=settings.TAXONOMY_CATEGORY_URL,
                                      fallback_path=
                                      settings.TAXONOMY_CATEGORY_PATH)),
    TaxonomyType.ingredient.name:
        CachedStore(functools.partial(fetch_taxonomy,
                                      url=settings.TAXONOMY_INGREDIENT_URL,
                                      fallback_path=
                                      settings.TAXONOMY_INGREDIENT_PATH)),
    TaxonomyType.label.name:
        CachedStore(functools.partial(fetch_taxonomy,
                                      url=settings.TAXONOMY_LABEL_URL,
                                      fallback_path=
                                      settings.TAXONOMY_LABEL_PATH))
}
