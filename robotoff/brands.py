import json
from typing import Tuple, Dict, Optional

from robotoff import settings
from robotoff.products import ProductDataset
from robotoff.utils.cache import CachedStore


def get_brand_prefix():
    with settings.BRAND_PREFIX_PATH.open('r') as f:
        return set(tuple(x) for x in json.load(f))


def generate_barcode_prefix(barcode: str) -> str:
    if len(barcode) == 13:
        prefix = 7
        return barcode[:prefix] + "x" * (len(barcode) - prefix)

    raise ValueError("barcode prefix only works on EAN-13 barcode "
                     "(here: {})".format(barcode))


def compute_brand_prefix(product_dataset: ProductDataset,
                         threshold: Optional[int] = None) -> Dict[Tuple[str, str], int]:
    count: Dict[Tuple[str, str], int] = {}

    for product in (product_dataset.stream()
                                   .filter_nonempty_tag_field('brands_tags')
                                   .filter_nonempty_text_field('code')):
        brand_tags = set(x for x in product['brands_tags'] if x)
        barcode = product['code']

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
    counts = compute_brand_prefix(product_dataset,
                                  threshold=count_threshold)

    brand_prefixes = list(counts.keys())

    with settings.BRAND_PREFIX_PATH.open('w') as f:
        json.dump(brand_prefixes, f)


BRAND_PREFIX_STORE = CachedStore(fetch_func=get_brand_prefix,
                                 expiration_interval=None)


if __name__ == "__main__":
    save_brand_prefix(count_threshold=2)
