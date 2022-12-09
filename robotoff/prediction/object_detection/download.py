import pathlib

from robotoff import settings
from robotoff.off import generate_image_url
from robotoff.products import ProductDataset
from robotoff.utils import get_logger, http_session
from robotoff.utils.types import JSONType

logger = get_logger()

JSONL_SHUF_DATASET_PATH = settings.DATASET_DIR / "products-shuf.jsonl.gz"
ds = ProductDataset(JSONL_SHUF_DATASET_PATH)
IMAGE_DATASET_DIR = settings.PROJECT_DIR / "image_dataset"
NUTRITION_TABLE_IMAGE_DIR = IMAGE_DATASET_DIR / "nutrition-table-2"


def load_seen_set() -> set[str]:
    seen_set = set()

    with open(IMAGE_DATASET_DIR / "dataset.txt") as f:
        for line in f:
            if line:
                line = line.strip("\n")
                barcode, _ = line.split("_")
                seen_set.add(barcode)

    return seen_set


def save_image(
    directory: pathlib.Path, image_meta: JSONType, barcode: str, override: bool = False
):
    image_id = image_meta["imgid"]
    image_name = "{}_{}.jpg".format(barcode, image_id)
    image_path = directory / image_name

    if image_path.exists() and not override:
        return

    image_url = generate_image_url(barcode, image_id)
    logger.info("Downloading image {}".format(image_url))
    r = http_session.get(image_url)

    with open(str(image_path), "wb") as fd:
        logger.info("Saving image in {}".format(image_path))
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)


seen_set = load_seen_set()
count = 0

for product in (
    ds.stream()
    .filter_by_state_tag("en:complete")
    .filter_by_country_tag("en:france")
    .filter_nonempty_text_field("code")
    .filter_nonempty_tag_field("images")
):
    barcode = product["code"]

    if barcode in seen_set:
        print("Product already seen: {}".format(barcode))
        continue

    has_nutrition = False
    has_front = False

    for image_key, image_meta in product.get("images", {}).items():
        if not has_nutrition and image_key.startswith("nutrition"):
            has_nutrition = True
            save_image(NUTRITION_TABLE_IMAGE_DIR, image_meta, barcode)
            count += 1
            continue

        elif not has_front and image_key.startswith("front"):
            has_front = True
            save_image(NUTRITION_TABLE_IMAGE_DIR, image_meta, barcode)
            count += 1
            continue

    if count >= 600:
        print("Breaking")
        print(count)
        break
