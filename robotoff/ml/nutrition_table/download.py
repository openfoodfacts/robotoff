import pathlib
import requests

from robotoff.off import generate_image_url
from robotoff.products import ProductDataset
from robotoff import settings
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger()

ds = ProductDataset(settings.JSONL_DATASET_PATH)
IMAGE_DATASET_DIR = settings.PROJECT_DIR / 'image_dataset'
NUTRITION_IMAGE_DATASET_DIR = IMAGE_DATASET_DIR / 'nutrition'
FRONT_IMAGE_DATASET_DIR = IMAGE_DATASET_DIR / 'front'


def save_image(directory: pathlib.Path,
               image_meta: JSONType,
               barcode: str,
               override: bool = False):
    image_name = image_meta['imgid']
    image_full_name = "{}_{}.jpg".format(barcode, image_name)
    image_path = directory / image_full_name

    if image_path.exists() and not override:
        return

    image_url = generate_image_url(barcode,
                                   image_name)
    logger.info("Downloading image {}".format(image_url))
    r = requests.get(image_url)

    with open(str(image_path), 'wb') as fd:
        logger.info("Saving image in {}".format(image_path))
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)


count = 0

for product in (ds.stream().filter_by_state_tag('en:complete')
                           .filter_nonempty_text_field('code')
                           .filter_nonempty_tag_field('images')):
    barcode = product['code']
    has_nutrition = False
    has_front = False

    for image_key, image_meta in product.get('images', []).items():
        if not has_nutrition and image_key.startswith('nutrition'):
            has_nutrition = True
            save_image(NUTRITION_IMAGE_DATASET_DIR, image_meta, barcode)
            continue

        elif not has_front and image_key.startswith('front'):
            has_front = False
            save_image(FRONT_IMAGE_DATASET_DIR, image_meta, barcode)
            continue

    if count >= 100:
        break

    count += 1
