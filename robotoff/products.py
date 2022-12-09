import abc
import datetime
import enum
import gzip
import json
import os
import pathlib
import shutil
import tempfile
from typing import Iterable, Iterator, Optional, Union

import requests
from pymongo import MongoClient

from robotoff import settings
from robotoff.mongo import MONGO_CLIENT_CACHE
from robotoff.utils import get_logger, gzip_jsonl_iter, http_session, jsonl_iter
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def get_image_id(image_path: str) -> Optional[str]:
    """Return the image ID from an image path.

    :param image_path: the image path (ex: /322/247/762/7888/2.jpg)
    :return: the image ID ("2" in the previous example) or None if the image
    is not "raw" (not digit-numbered)
    """
    image_id = pathlib.Path(image_path).stem

    if image_id.isdigit():
        return image_id

    return None


def is_valid_image(images: JSONType, image_path: str) -> bool:
    image_id = pathlib.Path(image_path).stem
    if not image_id.isdigit():
        return False

    return image_id in images


def is_nutrition_image(
    images: JSONType, image_path: str, lang: Optional[str] = None
) -> bool:
    return is_special_image(images, image_path, "nutrition", lang)


def has_nutrition_image(images: JSONType, lang: Optional[str] = None) -> bool:
    return has_special_image(images, "nutrition", lang)


def has_special_image(images: JSONType, key: str, lang: Optional[str] = None) -> bool:
    field_name = "{}_".format(key) if lang is None else "{}_{}".format(key, lang)
    for image_key in images:
        if image_key.startswith(field_name):
            return True

    return False


def is_special_image(
    images: JSONType, image_path: str, image_type: str, lang: Optional[str] = None
) -> bool:
    if not is_valid_image(images, image_path):
        return False

    image_id = pathlib.Path(image_path).stem

    for image_key, image_data in images.items():
        if (
            image_key.startswith(image_type)
            and str(image_data.get("imgid")) == image_id
        ):
            if lang is None:
                return True

            elif image_key.endswith("_{}".format(lang)):
                return True

    return False


def minify_product_dataset(dataset_path: pathlib.Path, output_path: pathlib.Path):
    if dataset_path.suffix == ".gz":
        jsonl_iter_func = gzip_jsonl_iter
    else:
        jsonl_iter_func = jsonl_iter

    with gzip.open(output_path, "wt", encoding="utf-8") as output_:
        for item in jsonl_iter_func(dataset_path):
            available_fields = Product.get_fields()

            minified_item = dict(
                (
                    (field, value)
                    for (field, value) in item.items()
                    if field in available_fields
                )
            )
            output_.write(json.dumps(minified_item) + "\n")


def get_product_dataset_etag() -> Optional[str]:
    if not settings.JSONL_DATASET_ETAG_PATH.is_file():
        return None

    with open(settings.JSONL_DATASET_ETAG_PATH, "r") as f:
        return f.readline()


def save_product_dataset_etag(etag: str):
    with open(settings.JSONL_DATASET_ETAG_PATH, "w") as f:
        return f.write(etag)


def fetch_dataset(minify: bool = True) -> bool:
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = pathlib.Path(tmp_dir)
        output_path = output_dir / "products.jsonl.gz"
        etag = download_dataset(output_path)

        logger.info("Checking dataset file integrity")
        if not is_valid_dataset(output_path):
            return False

        if minify:
            minify_path = output_dir / "products-min.jsonl.gz"
            logger.info("Minifying product JSONL")
            minify_product_dataset(output_path, minify_path)

        logger.info("Moving file(s) to dataset directory")
        shutil.copy(str(output_path), settings.JSONL_DATASET_PATH)

        if minify:
            shutil.copy(str(minify_path), settings.JSONL_MIN_DATASET_PATH)

        save_product_dataset_etag(etag)
        logger.info("Dataset fetched")
        return True


def has_dataset_changed() -> bool:
    etag = get_product_dataset_etag()

    if etag is not None:
        r = requests.head(settings.JSONL_DATASET_URL)

        current_etag = r.headers.get("ETag", "").strip("'\"")

        if current_etag == etag:
            logger.info("Dataset ETag has not changed")
            return False

    return True


def download_dataset(output_path: os.PathLike) -> str:
    r = http_session.get(settings.JSONL_DATASET_URL, stream=True)
    current_etag = r.headers.get("ETag", "").strip("'\"")

    logger.info("Dataset has changed, downloading file")
    logger.debug("Saving temporary file in {}".format(output_path))

    with open(output_path, "wb") as f:
        shutil.copyfileobj(r.raw, f)

    return current_etag


def is_valid_dataset(dataset_path: pathlib.Path) -> bool:
    """Check the dataset integrity: readable end to end and with a minimum number of products.
    This is used to spot corrupted archive files."""
    dataset = ProductDataset(dataset_path)
    try:
        count = dataset.count()
    except Exception as e:
        logger.error("Exception raised during dataset iteration", exc_info=e)
        return False

    if count < settings.DATASET_CHECK_MIN_PRODUCT_COUNT:
        logger.error(
            "Dataset has %s products, less than minimum of %s products",
            count,
            settings.DATASET_CHECK_MIN_PRODUCT_COUNT,
        )
        return False

    return True


class ComparisonOperator(enum.Enum):
    eq = 1
    gt = 2
    geq = 3
    lt = 4
    leq = 5

    @classmethod
    def get_from_string(cls, value: str):
        for operator in cls:
            if operator.name == value:
                return operator

        raise ValueError("unknown operator: {}".format(value))


def apply_comparison_operator(
    value_1, value_2, comparison_operator: ComparisonOperator
) -> bool:
    try:
        if comparison_operator == ComparisonOperator.eq:
            return value_1 == value_2

        elif comparison_operator == ComparisonOperator.gt:
            return value_1 > value_2

        elif comparison_operator == ComparisonOperator.geq:
            return value_1 >= value_2

        elif comparison_operator == ComparisonOperator.lt:
            return value_1 < value_2

        else:
            return value_1 <= value_2
    except TypeError:
        return False


class ProductStream:
    """Starting for a stream of dict representing products,
    provides a stream with filter methods to narrow down data.
    """

    def __init__(self, iterator: Iterable[JSONType]):
        self.iterator: Iterable[JSONType] = iterator

    def __iter__(self) -> Iterator[JSONType]:
        yield from self.iterator

    def filter_by_country_tag(self, country_tag: str) -> "ProductStream":
        filtered = (
            product
            for product in self.iterator
            if country_tag in (product.get("countries_tags") or [])
        )
        return ProductStream(filtered)

    def filter_by_state_tag(self, state_tag: str) -> "ProductStream":
        filtered = (
            product
            for product in self.iterator
            if state_tag in (product.get("states_tags") or [])
        )
        return ProductStream(filtered)

    def filter_text_field(self, field: str, value: str):
        filtered = (
            product for product in self.iterator if product.get(field, "") == value
        )
        return ProductStream(filtered)

    def filter_number_field(
        self,
        field: str,
        ref: Union[int, float],
        default: Union[int, float],
        operator: str = "eq",
    ) -> "ProductStream":
        operator_ = ComparisonOperator.get_from_string(operator)
        filtered = (
            product
            for product in self.iterator
            if apply_comparison_operator(product.get(field, default), ref, operator_)
        )
        return ProductStream(filtered)

    def filter_nonempty_text_field(self, field: str) -> "ProductStream":
        filtered = (
            product for product in self.iterator if (product.get(field) or "") != ""
        )
        return ProductStream(filtered)

    def filter_empty_text_field(self, field: str) -> "ProductStream":
        filtered = (
            product for product in self.iterator if not (product.get(field) or "") != ""
        )
        return ProductStream(filtered)

    def filter_nonempty_tag_field(self, field: str) -> "ProductStream":
        filtered = (product for product in self.iterator if (product.get(field) or []))
        return ProductStream(filtered)

    def filter_empty_tag_field(self, field: str) -> "ProductStream":
        filtered = (
            product for product in self.iterator if not (product.get(field) or [])
        )
        return ProductStream(filtered)

    def filter_by_modified_datetime(
        self,
        from_t: Optional[datetime.datetime] = None,
        to_t: Optional[datetime.datetime] = None,
    ):
        if from_t is None and to_t is None:
            raise ValueError("one of `from_t` or `to_t` must be provided")

        if from_t:
            from_timestamp = from_t.timestamp()
            filtered = (
                product
                for product in self.iterator
                if "last_modified_t" in product
                and product["last_modified_t"] >= from_timestamp
            )

        elif to_t:
            to_timestamp = to_t.timestamp()
            filtered = (
                product
                for product in self.iterator
                if "last_modified_t" in product
                and product["last_modified_t"] <= to_timestamp
            )

        return ProductStream(filtered)

    def take(self, count: int):
        for i, item in enumerate(self):
            if i >= count:
                break

            yield item

    def iter(self) -> Iterable[JSONType]:
        return iter(self)

    def iter_product(self) -> Iterable["Product"]:
        for item in self:
            yield Product(item)

    def collect(self) -> list[JSONType]:
        return list(self)


class ProductDataset:
    """Handles the iteration over products dataset
    contained in an eventually gziped file with one json by line.
    """

    def __init__(self, jsonl_path):
        self.jsonl_path = jsonl_path

    def stream(self) -> ProductStream:
        json_path_str = str(self.jsonl_path)

        if json_path_str.endswith(".gz"):
            iterator = gzip_jsonl_iter(json_path_str)
        else:
            iterator = jsonl_iter(json_path_str)

        return ProductStream(iterator)

    def count(self) -> int:
        count = 0
        for _ in self.stream():
            count += 1

        return count

    @classmethod
    def load(cls):
        return cls(settings.JSONL_DATASET_PATH)


class Product:
    """Product class."""

    __slots__ = (
        "barcode",
        "countries_tags",
        "categories_tags",
        "emb_codes_tags",
        "labels_tags",
        "quantity",
        "expiration_date",
        "brands_tags",
        "stores_tags",
        "unique_scans_n",
        "images",
    )

    def __init__(self, product: JSONType):
        self.barcode: Optional[str] = product.get("code")
        self.countries_tags: list[str] = product.get("countries_tags") or []
        self.categories_tags: list[str] = product.get("categories_tags") or []
        self.emb_codes_tags: list[str] = product.get("emb_codes_tags") or []
        self.labels_tags: list[str] = product.get("labels_tags") or []
        self.quantity: Optional[str] = product.get("quantity") or None
        self.expiration_date: Optional[str] = product.get("expiration_date") or None
        self.brands_tags: list[str] = product.get("brands_tags") or []
        self.stores_tags: list[str] = product.get("stores_tags") or []
        self.unique_scans_n: int = product.get("unique_scans_n") or 0
        self.images: JSONType = product.get("images") or {}

    @staticmethod
    def get_fields():
        return {
            "code",
            "countries_tags",
            "categories_tags",
            "emb_codes_tags",
            "labels_tags",
            "quantity",
            "expiration_date",
            "brands_tags",
            "stores_tags",
            "unique_scans_n",
            "images",
        }


class ProductStore(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __len__(self):
        pass

    @abc.abstractmethod
    def __getitem__(self, item):
        pass


class MemoryProductStore(ProductStore):
    def __init__(self, store: dict[str, Product]):
        self.store: dict[str, Product] = store

    def __len__(self):
        return len(self.store)

    @classmethod
    def load_from_path(cls, path: str):
        logger.info("Loading product store")
        ds = ProductDataset(path)
        stream = ds.stream()

        store: dict[str, Product] = {}

        for product in stream.iter_product():
            if product.barcode:
                store[product.barcode] = product

        return cls(store)

    @classmethod
    def load_min(cls):
        return cls.load_from_path(settings.JSONL_MIN_DATASET_PATH)

    @classmethod
    def load_full(cls):
        return cls.load_from_path(settings.JSONL_DATASET_PATH)

    def __getitem__(self, item) -> Optional[Product]:
        return self.store.get(item)

    def __iter__(self) -> Iterator[Product]:
        return iter(self.store.values())


class DBProductStore(ProductStore):
    def __init__(self, client: MongoClient):
        self.client = client
        self.db = self.client.off
        self.collection = self.db.products

    def __len__(self):
        return len(self.collection.estimated_document_count())

    def get_product(
        self, barcode: str, projection: Optional[list[str]] = None
    ) -> Optional[JSONType]:
        return self.collection.find_one({"code": barcode}, projection)

    def __getitem__(self, barcode: str) -> Optional[Product]:
        product = self.get_product(barcode)

        if product:
            return Product(product)

        return None

    def __iter__(self):
        yield from self.iter()

    def iter_product(self, projection: Optional[list[str]] = None):
        yield from (Product(p) for p in self.collection.find(projection=projection))


def load_min_dataset() -> ProductStore:
    ps = MemoryProductStore.load_min()
    logger.info("product store loaded ({} items)".format(len(ps)))
    return ps


def get_product_store() -> DBProductStore:
    mongo_client = MONGO_CLIENT_CACHE.get()
    return DBProductStore(client=mongo_client)


def get_product(
    barcode: str, projection: Optional[list[str]] = None
) -> Optional[JSONType]:
    """Get product from MongoDB.

    :param barcode: barcode of the product to fetch
    :param projection: list of fields to retrieve, if not provided all fields
    are queried
    :return: the product as a dict or None if it was not found
    """
    mongo_client = MONGO_CLIENT_CACHE.get()
    return mongo_client.off.products.find_one({"code": barcode}, projection)


CACHED_PRODUCT_STORE = CachedStore(load_min_dataset)
