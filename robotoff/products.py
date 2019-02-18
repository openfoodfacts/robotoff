import gzip
import json
import os
import pathlib
import shutil
import tempfile
from typing import List, Iterable, Dict, Optional

import requests

from robotoff.utils import jsonl_iter, gzip_jsonl_iter, get_logger
from robotoff import settings
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType

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


def get_product_dataset_etag() -> Optional[str]:
    if not settings.JSONL_DATASET_ETAG_PATH.is_file():
        return None

    with open(settings.JSONL_DATASET_ETAG_PATH, 'r') as f:
        return f.readline()


def save_product_dataset_etag(etag: str):
    with open(settings.JSONL_DATASET_ETAG_PATH, 'w') as f:
        return f.write(etag)


def fetch_dataset():
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = pathlib.Path(tmp_dir)
        output_path = output_dir / 'products.jsonl.gz'
        etag = download_dataset(output_path)
        minify_path = output_dir / 'products-min.jsonl.gz'

        logger.info("Minifying product JSONL")
        minify_product_dataset(output_path, minify_path)

        logger.info("Moving files to dataset directory")
        shutil.move(output_path, settings.JSONL_DATASET_PATH)
        shutil.move(minify_path, settings.JSONL_MIN_DATASET_PATH)
        save_product_dataset_etag(etag)
        logger.info("Dataset fetched")


def has_dataset_changed() -> bool:
    etag = get_product_dataset_etag()

    if etag is not None:
        r = requests.head(settings.JSONL_DATASET_URL)

        current_etag = r.headers.get('ETag', '').strip("'\"")

        if current_etag == etag:
            logger.info("Dataset ETag has not changed")
            return False

    return True


def download_dataset(output_path: os.PathLike) -> str:
    r = requests.get(settings.JSONL_DATASET_URL,
                     stream=True)
    current_etag = r.headers.get('ETag', '').strip("'\"")

    logger.info("Dataset has changed, downloading file")
    logger.debug("Saving temporary file in {}".format(output_path))

    with open(output_path, 'wb') as f:
        shutil.copyfileobj(r.raw, f)

    return current_etag


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
    __slots__ = ('barcode', 'countries_tags', 'categories_tags',
                 'emb_codes_tags', 'labels_tags')

    def __init__(self, product: JSONType):
        self.barcode = product.get('code')
        self.countries_tags = product.get('countries_tags') or []
        self.categories_tags = product.get('categories_tags') or []
        self.emb_codes_tags = product.get('emb_codes_tags') or []
        self.labels_tags = product.get('labels_tags') or []

    @staticmethod
    def get_fields():
        return {
            'code',
            'countries_tags',
            'categories_tags',
            'emb_codes_tags',
            'labels_tags',
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

    @classmethod
    def load_min_dataset(cls):
        product_store = ProductStore()
        product_store.load(settings.JSONL_MIN_DATASET_PATH, False)
        return product_store

    def __getitem__(self, item):
        return self.store.get(item)


CACHED_PRODUCT_STORE = CachedStore(lambda: ProductStore.load_min_dataset())
