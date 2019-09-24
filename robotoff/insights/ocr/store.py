import re
from typing import List, Dict, Tuple, Set

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRResult, OCRRegex, OCRField
from robotoff.utils import text_file_iter


def get_store_tag(store: str) -> str:
    return (store.lower()
                 .replace(' & ', '-')
                 .replace(' ', '-')
                 .replace("'", '-'))


def store_sort_key(item):
    """Sorting function for STORE_DATA items.
    For the regex to work correctly, we want the longest store names to
    appear first.
    """
    store, _ = item

    return -len(store), store


def get_sorted_stores() -> List[Tuple[str, str]]:
    sorted_stores: Dict[str, str] = {}

    for item in text_file_iter(settings.OCR_STORES_DATA_PATH):
        if '||' in item:
            store, regex_str = item.split('||')
        else:
            store = item
            regex_str = re.escape(item.lower())

        sorted_stores[store] = regex_str

    return sorted(sorted_stores.items(), key=store_sort_key)


SORTED_STORES = get_sorted_stores()
STORE_REGEX_STR = "|".join(r"((?<!\w){}(?!\w))".format(pattern)
                           for _, pattern in SORTED_STORES)
NOTIFY_STORES: Set[str] = set(
    text_file_iter(settings.OCR_STORES_NOTIFY_DATA_PATH))
STORE_REGEX = OCRRegex(re.compile(STORE_REGEX_STR),
                       field=OCRField.full_text_contiguous,
                       lowercase=True)


def find_stores(ocr_result: OCRResult) -> List[Dict]:
    results = []

    text = ocr_result.get_text(STORE_REGEX)

    if not text:
        return []

    for match in STORE_REGEX.regex.finditer(text):
        groups = match.groups()

        for idx, match_str in enumerate(groups):
            if match_str is not None:
                store, _ = SORTED_STORES[idx]
                results.append({
                    'store': store,
                    'store_tag': get_store_tag(store),
                    'text': match_str,
                    'notify': store in NOTIFY_STORES,
                })
                break

    return results
