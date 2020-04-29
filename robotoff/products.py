import abc
import datetime
import enum
import gzip
import json
import os
import pathlib
import shutil
import tempfile
from typing import List, Iterable, Dict, Optional, Iterator, Union

from pymongo import MongoClient
import requests

from robotoff.off import http_session
from robotoff.utils import jsonl_iter, gzip_jsonl_iter, get_logger
from robotoff import settings
from robotoff.mongo import MONGO_CLIENT_CACHE
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def is_valid_image(images: JSONType, image_path: str) -> bool:
    image_id = pathlib.Path(image_path).stem
    if not image_id.isdigit():
        return False

    return image_id in images


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
        shutil.move(str(output_path), settings.JSONL_DATASET_PATH)

        if minify:
            shutil.move(str(minify_path), settings.JSONL_MIN_DATASET_PATH)

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
            "Dataset has {} products, less than minimum of {} products".format(
                count, settings.DATASET_CHECK_MIN_PRODUCT_COUNT
            )
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

    def collect(self) -> List[JSONType]:
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

    def count(self) -> int:
        count = 0
        for product in self.stream():
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
        self.barcode = product.get("code")
        self.countries_tags = product.get("countries_tags") or []
        self.categories_tags = product.get("categories_tags") or []
        self.emb_codes_tags = product.get("emb_codes_tags") or []
        self.labels_tags = product.get("labels_tags") or []
        self.quantity = product.get("quantity") or None
        self.expiration_date = product.get("expiration_date") or None
        self.brands_tags = product.get("brands_tags") or []
        self.stores_tags = product.get("stores_tags") or []
        self.unique_scans_n = product.get("unique_scans_n") or 0
        self.images = product.get("images") or {}

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
    def __init__(self, store: Dict[str, Product]):
        self.store: Dict[str, Product] = store

    def __len__(self):
        return len(self.store)

    @classmethod
    def load_from_path(cls, path: str):
        logger.info("Loading product store")
        ds = ProductDataset(path)
        stream = ds.stream()

        store: Dict[str, Product] = {}

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

    def __iter__(self) -> Iterable[Product]:
        return iter(self.store.values())


class DBProductStore(ProductStore):
    def __init__(self, client: MongoClient):
        self.client = client
        self.db = self.client.off
        self.collection = self.db.products

    def __len__(self):
        return len(self.collection.estimated_document_count())

    def get_product(
        self, barcode: str, projection: Optional[List[str]] = None
    ) -> Optional[JSONType]:
        return self.collection.find_one({"code": barcode}, projection)

    def __getitem__(self, barcode: str) -> Optional[Product]:
        product = self.get_product(barcode)

        if product:
            return Product(product)

        return None

    def __iter__(self):
        raise NotImplementedError("cannot iterate over database product store")


def load_min_dataset() -> ProductStore:
    ps = MemoryProductStore.load_min()
    logger.info("product store loaded ({} items)".format(len(ps)))
    return ps


def get_product_store() -> DBProductStore:
    mongo_client = MONGO_CLIENT_CACHE.get()
    return DBProductStore(client=mongo_client)


CACHED_PRODUCT_STORE = CachedStore(load_min_dataset)
