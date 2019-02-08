import gzip
import json
import os
import pathlib
import shutil
import tempfile
import threading
from queue import Queue, Empty
from threading import Thread
from typing import List, Iterable, Dict

import requests

from robotoff.utils import jsonl_iter, gzip_jsonl_iter, get_logger
from robotoff import settings

logger = get_logger(__name__)


def minify_product_dataset(dataset_path: pathlib.Path,
                           output_path: pathlib.Path):
    if dataset_path.suffix == '.gz':
        jsonl_iter_func = gzip_jsonl_iter
    else:
        jsonl_iter_func = jsonl_iter

    with gzip.open(output_path, 'wt') as output_:
        for item in jsonl_iter_func(dataset_path):
            available_fields = Product.get_fields()

            minified_item = dict(((field, value)
                                  for (field, value) in item.items()
                                  if field in available_fields))
            output_.write(json.dumps(minified_item) + '\n')


def fetch_dataset():
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger.debug("Saving temporary file in {}".format(tmp_dir))
        output_dir = pathlib.Path(tmp_dir)
        output_path = output_dir / 'products.jsonl.gz'
        download_dataset(output_path)
        minify_path = output_dir / 'products-min.jsonl.gz'

        logger.info("Minifying product JSONL")
        minify_product_dataset(output_path, minify_path)

        logger.info("Moving files to dataset directory")
        output_path.rename(settings.JSONL_DATASET_PATH)
        minify_path.rename(settings.JSONL_MIN_DATASET_PATH)
        logger.info("Dataset fetched")


def download_dataset(output_path: os.PathLike) -> None:
    r = requests.get(settings.JSONL_DATASET_URL, stream=True)

    with open(output_path, 'wb') as f:
        shutil.copyfileobj(r.raw, f)


class ProductStream:
    def __init__(self, iterator):
        self.iterator = iterator

    def __iter__(self):
        yield from self.iterator

    def filter_by_country_tag(self, country_tag: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if country_tag in (product.get('countries_tags') or []))
        return ProductStream(filtered)

    def filter_by_state_tag(self, state_tag: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if state_tag in (product.get('states_tags') or []))
        return ProductStream(filtered)

    def filter_nonempty_text_field(self, field: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if (product.get(field) or "") != "")
        return ProductStream(filtered)

    def filter_empty_text_field(self, field: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if not (product.get(field) or "") != "")
        return ProductStream(filtered)

    def filter_nonempty_tag_field(self, field: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if (product.get(field) or []))
        return ProductStream(filtered)

    def filter_empty_tag_field(self, field: str) -> 'ProductStream':
        filtered = (product for product in self.iterator
                    if not (product.get(field) or []))
        return ProductStream(filtered)

    def iter(self) -> Iterable[Dict]:
        return iter(self)

    def iter_product(self):
        for item in self:
            yield Product(item)

    def collect(self) -> List[Dict]:
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


class Product:
    """Product class."""
    __slots__ = ('barcode', 'countries_tags', 'categories_tags', 'emb_codes_tags')

    def __init__(self, product: Dict):
        self.barcode = product.get('code')
        self.countries_tags = product.get('countries_tags') or []
        self.categories_tags = product.get('categories_tags') or []
        self.emb_codes_tags = product.get('emb_codes_tags') or []

    @staticmethod
    def get_fields():
        return {
            'code',
            'countries_tags',
            'categories_tags',
            'emb_codes_tags',
        }


class ProductStore:
    def __init__(self):
        self.store: Dict[str, Product] = {}

    def load(self, path: str, reset: bool=True):
        logger.info("Loading product store")
        ds = ProductDataset(path)
        stream = ds.stream()

        seen = set()
        for product in stream.iter_product():
            if product.barcode:
                seen.add(product.barcode)
                self.store[product.barcode] = product

        if reset:
            for key in set(self.store.keys()).difference(seen):
                self.store.pop(key)

        logger.info("product store loaded ({} items added)".format(len(seen)))

    def __getitem__(self, item):
        return self.store.get(item)


class ThreadEvent:
    def __init__(self, event_type: str, meta: Dict):
        self.event_type = event_type
        self.meta = meta


class ProductStoreThread(Thread):
    def __init__(self, event_q):
        super().__init__(name="product-store-thread")
        self.event_q: Queue[ThreadEvent] = event_q
        self.stop_flag: threading.Event = threading.Event()
        self.product_store = ProductStore()

    def run(self):
        while not self.stop_flag.isSet():
            try:
                event = self.event_q.get(True, 0.05)
                self.process_event(event)
            except Empty:
                continue

    def process_event(self, event: ThreadEvent):
        if event.event_type == 'load':
            self.load(**event.meta)
        else:
            logger.warning("unknown event type: {}".format(event.event_type))

    def load(self, path: str, reset: bool=True):
        logger.info("Loading product store from path {}".format(path))
        self.product_store.load(path, reset)
        logger.info("Product store loaded")

    def join(self, timeout=None):
        self.stop_flag.set()
        super(ProductStoreThread, self).join(timeout)


if __name__ == "__main__":
    store = ProductStore()
    store.load(settings.JSONL_DATASET_PATH)
