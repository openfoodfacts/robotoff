import collections
import json
from typing import Dict, List


class Category:
    __slots__ = ('id', 'names', 'parents')

    def __init__(self, id, names, parents=None):
        self.id = id
        self.names = names
        self.parents = parents or []

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

    @classmethod
    def from_data(cls, data):
        categories_map = {}

        for category, category_data in data.items():
            if category not in categories_map:
                categories_map[category] = cls(id=category,
                                               names=category_data.get('names', []))

        for category, category_data in data.items():
            category_item = categories_map[category]
            parents = [categories_map[ref] for ref in category_data.get('parents', [])]
            category_item.parents = parents

        return categories_map

    @staticmethod
    def find_deepest_item(items: List[str], data: 'CategoryTaxonomy'):
        excluded = set()

        if not any(True if item in data.keys() else False for item in items):
            # The key is not present in the taxonomy
            raise ValueError("Could not find any item of {} in taxonomy".format(items))

        items = [i for i in items if i in data]

        if len(items) == 1:
            return items[0]

        for item in items:
            if item not in data:
                excluded.add(item)
                continue

            for second_item in (i for i in items if i not in excluded):
                if second_item not in data:
                    excluded.add(item)
                    continue

                if item == second_item:
                    continue

                if data[item].is_child_of(data[second_item]):
                    excluded.add(second_item)

        return [i for i in items if i not in excluded][0]


CategoryTaxonomy = Dict[str, Category]


def parse_category_json(data_path):
    with open(str(data_path), 'r') as f:
        return json.load(f)


def generate_category_hierarchy(data, category_to_index, root):
    categories_hierarchy = collections.defaultdict(set)

    for category, category_data in data.items():
        category_index = category_to_index[category]

        if not category_data.get('parents', []):
            categories_hierarchy[root].add(category_index)

        children = category_data.get('children', [])

        children_indexes = set([category_to_index[c]
                                for c in children
                                if c in category_to_index])

        categories_hierarchy[category_index] = \
            categories_hierarchy[category_index].union(children_indexes)

    categories_hierarchy_list = {}
    for category in categories_hierarchy.keys():
        categories_hierarchy_list[category] = \
            list(categories_hierarchy[category])

    return categories_hierarchy_list
