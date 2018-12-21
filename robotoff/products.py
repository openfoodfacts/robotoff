from typing import List

from robotoff.utils import jsonl_iter, gzip_jsonl_iter


class ProductStream:
    def __init__(self, iterator):
        self.iterator = iterator

    def __iter__(self):
        yield from self.iterator

    def filter_by_country_tag(self, country_tag: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if country_tag in (product.get('countries_tags') or []))
        return ProductStream(filtered)

    def filter_nonempty_text_field(self, field: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if (product.get(field) or "") != "")
        return ProductStream(filtered)

    def filter_nonempty_tag_field(self, field: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if (product.get(field) or []))
        return ProductStream(filtered)

    def collect(self) -> List[dict]:
        return list(self)


class ProductDataset:
    def __init__(self, jsonl_path):
        self.jsonl_path = jsonl_path

    def stream(self) -> ProductStream:
        json_path_str = str(self.jsonl_path)

        if json_path_str.endswith(".gz"):
            iterator = gzip_jsonl_iter(json_path_str)
        else:
            iterator = jsonl_iter(json_path_str)

        return ProductStream(iterator)
