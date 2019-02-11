import json
import threading
from queue import Queue, Empty
from threading import Thread
from typing import Dict, List

from robotoff.insights.importer import InsightImporterFactory
from robotoff.models import db
from robotoff.products import ProductStore, fetch_dataset, has_dataset_changed
from robotoff.utils import get_logger

logger = get_logger(__name__)


class ThreadEvent:
    def __init__(self, event_type: str, meta: Dict = None):
        self.event_type = event_type
        self.meta = meta


class WorkerThread(Thread):
    def __init__(self, event_q):
        super().__init__(name="product-store-thread")
        self.event_q: Queue[ThreadEvent] = event_q
        self.stop_flag: threading.Event = threading.Event()
        self.lock = threading.Lock()

    def run(self):
        while not self.stop_flag.isSet():
            try:
                event = self.event_q.get(True, 0.05)
                with self.lock:
                    self.process_event(event)
            except Empty:
                continue

    def process_event(self, event: ThreadEvent):
        if event.event_type == 'download':
            logger.info("download thread event received")
            self.download()
        elif event.event_type == 'import':
            logger.info("import thread event received")
            import_items(**event.meta)
        else:
            logger.warning("unknown event type: {}".format(event.event_type))

    @staticmethod
    def download():
        if has_dataset_changed():
            fetch_dataset()

    def join(self, timeout=None):
        self.stop_flag.set()
        super(WorkerThread, self).join(timeout)


def import_items(insight_type: str, items: List[str]):
    importer_cls = InsightImporterFactory.create(insight_type)

    if importer_cls.need_product_store():
        product_store = ProductStore()
        product_store.load_min_dataset()
        importer = importer_cls(product_store)
    else:
        importer = importer_cls()

    with db.atomic():
        importer.import_insights((json.loads(l) for l in items))
        logger.info("Import finished")
