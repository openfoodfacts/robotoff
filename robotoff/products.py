import threading
from queue import Queue, Empty
from threading import Thread
from typing import List, Iterable, Dict

from robotoff.utils import jsonl_iter, gzip_jsonl_iter, get_logger

logger = get_logger(__name__)


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
    from robotoff import settings
    store = ProductStore()
    store.load(settings.JSONL_DATASET_PATH)
