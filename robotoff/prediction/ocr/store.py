import functools
import re
from typing import Union

from robotoff import settings
from robotoff.types import Prediction, PredictionType
from robotoff.utils import text_file_iter

from .dataclass import OCRField, OCRRegex, OCRResult, get_match_bounding_box, get_text


def get_store_tag(store: str) -> str:
    return store.lower().replace(" & ", "-").replace(" ", "-").replace("'", "-")


def store_sort_key(item):
    """Sorting function for STORE_DATA items.
    For the regex to work correctly, we want the longest store names to
    appear first.
    """
    store, _ = item

    return -len(store), store


@functools.cache
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


@functools.cache
def get_store_ocr_regex() -> OCRRegex:
    sorted_stores = get_sorted_stores()
    store_regex_str = "|".join(
        r"((?<!\w){}(?!\w))".format(pattern) for _, pattern in sorted_stores
    )
    return OCRRegex(
        re.compile(store_regex_str, re.I), field=OCRField.full_text_contiguous
    )


@functools.cache
def get_notify_stores() -> set[str]:
    return set(text_file_iter(settings.OCR_STORES_NOTIFY_DATA_PATH))


def find_stores(content: Union[OCRResult, str]) -> list[Prediction]:
    results = []
    store_ocr_regex = get_store_ocr_regex()
    sorted_stores = get_sorted_stores()
    notify_stores = get_notify_stores()
    text = get_text(content, store_ocr_regex)

    if not text:
        return []

    for match in store_ocr_regex.regex.finditer(text):
        groups = match.groups()

        for idx, match_str in enumerate(groups):
            if match_str is not None:
                store, _ = sorted_stores[idx]
                data = {"text": match_str, "notify": store in notify_stores}
                if (
                    bounding_box := get_match_bounding_box(
                        content, match.start(), match.end()
                    )
                ) is not None:
                    data["bounding_box_absolute"] = bounding_box

                results.append(
                    Prediction(
                        type=PredictionType.store,
                        value=store,
                        value_tag=get_store_tag(store),
                        data=data,
                        predictor="regex",
                    )
                )
                break

    return results
