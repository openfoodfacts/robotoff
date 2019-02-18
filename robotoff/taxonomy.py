import functools
import json
from enum import Enum
from typing import List, Dict, Iterable, Optional

import requests

from robotoff import settings
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType


class TaxonomyType(Enum):
    category = 1
    ingredient = 2
    label = 3


class TaxonomyNode:
    __slots__ = ('id', 'names', 'parents')

    def __init__(self, identifier: str,
                 names: List[Dict[str, str]],
                 parents: List['TaxonomyNode'] = None):
        self.id: str = identifier
        self.names: Dict[str, str] = names
        self.parents: List['TaxonomyNode'] = parents or []

    def is_child_of(self, item):
        if not self.parents:
            return False

        if item in self.parents:
            return True

        for parent in self.parents:
            is_parent = parent.is_child_of(item)

            if is_parent:
                return True

        return False

    def get_localized_name(self, lang: str) -> str:
        if lang in self.names:
            return self.names[lang]

        return self.id

    def add_parents(self, parents: Iterable['TaxonomyNode']):
        for parent in parents:
            if parent not in self.parents:
                self.parents.append(parent)

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

    def get_localized_name(self, key: str, lang: str) -> str:
        if key not in self.nodes:
            return key

        return self.nodes[key].get_localized_name(lang)

    @classmethod
    def from_data(cls, data: JSONType) -> 'Taxonomy':
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
            return cls.from_data(data)


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

    return Taxonomy.from_data(data)


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
