import json
import operator
from typing import Tuple, Dict, Optional, List, Set

import requests

from robotoff import settings
from robotoff.products import ProductDataset
from robotoff.utils import dump_text, text_file_iter
from robotoff.utils.cache import CachedStore


def get_brand_prefix() -> Set:
    with settings.BRAND_PREFIX_PATH.open("r") as f:
        return set(tuple(x) for x in json.load(f))


def get_brand_blacklist() -> Set[str]:
    return set(text_file_iter(settings.OCR_TAXONOMY_BRANDS_BLACKLIST_PATH))


def generate_barcode_prefix(barcode: str) -> str:
    if len(barcode) == 13:
        prefix = 7
        return barcode[:prefix] + "x" * (len(barcode) - prefix)

    raise ValueError(
        "barcode prefix only works on EAN-13 barcode " "(here: {})".format(barcode)
    )


def compute_brand_prefix(
    product_dataset: ProductDataset, threshold: Optional[int] = None
) -> Dict[Tuple[str, str], int]:
    count: Dict[Tuple[str, str], int] = {}

    for product in (
        product_dataset.stream()
        .filter_nonempty_tag_field("brands_tags")
        .filter_nonempty_text_field("code")
    ):
        brand_tags = set(x for x in product["brands_tags"] if x)
        barcode = product["code"]

        if len(barcode) == 13:
            barcode_prefix = generate_barcode_prefix(barcode)

            for brand_tag in brand_tags:
                key = (brand_tag, barcode_prefix)
                count.setdefault(key, 0)
                count[key] += 1

    if threshold:
        for key in list(count.keys()):
            if count[key] < threshold:
                count.pop(key)

    return count


def save_brand_prefix(count_threshold: int):
    product_dataset = ProductDataset(settings.JSONL_DATASET_PATH)
    counts = compute_brand_prefix(product_dataset, threshold=count_threshold)

    brand_prefixes = list(counts.keys())

    with settings.BRAND_PREFIX_PATH.open("w") as f:
        json.dump(brand_prefixes, f)


def generate_brand_list(threshold: int) -> List[Tuple[str, str]]:
    brand_taxonomy = requests.get(settings.TAXONOMY_BRAND_URL).json()
    brand_count_list = requests.get(settings.OFF_BRANDS_URL).json()["tags"]

    brand_count = {tag["id"]: tag for tag in brand_count_list}
    brand_list = []

    for key in list(brand_taxonomy.keys()):
        name = brand_taxonomy[key]["name"]["en"]

        if key.startswith("en:"):
            key = key[3:]

        if brand_count.get(key, {}).get("products", 0) >= threshold:
            brand_list.append((key, name))

    return sorted(brand_list, key=operator.itemgetter(0))


def dump_taxonomy_brands(threshold: int):
    filtered_brands = generate_brand_list(threshold)
    filtered_brands = ("{}||{}".format(key, name) for key, name in filtered_brands)
    dump_text(settings.OCR_TAXONOMY_BRANDS_PATH, filtered_brands)


def in_barcode_range(
    brand_prefix: Set[Tuple[str, str]], brand_tag: str, barcode: str
) -> bool:
    """Check that the insight barcode is in the range of the detected
    brand barcode range.
    Return True if the check passes, False otherwise
    """
    if len(barcode) == 13:
        barcode_prefix = generate_barcode_prefix(barcode)
        key = (brand_tag, barcode_prefix)

        if key not in brand_prefix:
            return False

    return True


BRAND_PREFIX_STORE = CachedStore(fetch_func=get_brand_prefix, expiration_interval=None)
BRAND_BLACKLIST_STORE = CachedStore(
    fetch_func=get_brand_blacklist, expiration_interval=None
)

if __name__ == "__main__":
    save_brand_prefix(count_threshold=2)
