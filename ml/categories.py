import json


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
    def find_deepest_item(items, data):
        excluded = set()

        if not any(True if i in data else False for i in items):
            return items[0]

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


def generate_category_taxonomy(data_path):
    with open(str(data_path), 'r') as f:
        taxonomy_json = json.load(f)

    categories_map = Category.from_data(taxonomy_json)
    return categories_map

