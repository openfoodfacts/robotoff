import re
from typing import Set

from robotoff import settings
from robotoff.utils import text_file_iter


def test_check_ocr_stores():
    stores: Set[str] = set()

    for item in text_file_iter(settings.OCR_STORES_DATA_PATH):
        if '||' in item:
            store, regex_str = item.split('||')
        else:
            store = item
            regex_str = re.escape(item.lower())

        re.compile(regex_str)
        stores.add(store)

    for item in text_file_iter(settings.OCR_STORES_NOTIFY_DATA_PATH):
        assert item in stores
