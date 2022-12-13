import re
from typing import Union

from robotoff import settings
from robotoff.prediction.types import Prediction
from robotoff.types import PredictionType
from robotoff.utils import text_file_iter

from .dataclass import OCRField, OCRRegex, OCRResult, get_text


def get_store_tag(store: str) -> str:
    return store.lower().replace(" & ", "-").replace(" ", "-").replace("'", "-")


def store_sort_key(item):
    """Sorting function for STORE_DATA items.
    For the regex to work correctly, we want the longest store names to
    appear first.
    """
    store, _ = item

    return -len(store), store


def get_sorted_stores() -> list[tuple[str, str]]:
    sorted_stores: dict[str, str] = {}

    for item in text_file_iter(settings.OCR_STORES_DATA_PATH):
        if "||" in item:
            store, regex_str = item.split("||")
        else:
            store = item
            regex_str = re.escape(item.lower())

        sorted_stores[store] = regex_str

    return sorted(sorted_stores.items(), key=store_sort_key)


SORTED_STORES = get_sorted_stores()
STORE_REGEX_STR = "|".join(
    r"((?<!\w){}(?!\w))".format(pattern) for _, pattern in SORTED_STORES
)
NOTIFY_STORES: set[str] = set(text_file_iter(settings.OCR_STORES_NOTIFY_DATA_PATH))
STORE_REGEX = OCRRegex(
    re.compile(STORE_REGEX_STR), field=OCRField.full_text_contiguous, lowercase=True
)


def find_stores(content: Union[OCRResult, str]) -> list[Prediction]:
    results = []

    text = get_text(content, STORE_REGEX)

    if not text:
        return []

    for match in STORE_REGEX.regex.finditer(text):
        groups = match.groups()

        for idx, match_str in enumerate(groups):
            if match_str is not None:
                store, _ = SORTED_STORES[idx]
                results.append(
                    Prediction(
                        type=PredictionType.store,
                        value=store,
                        value_tag=get_store_tag(store),
                        data={"text": match_str, "notify": store in NOTIFY_STORES},
                        predictor="regex",
                    )
                )
                break

    return results
