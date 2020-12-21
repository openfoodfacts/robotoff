import tqdm

from robotoff import settings
from robotoff.models import db, ImageModel
from robotoff.off import generate_image_url
from robotoff.products import Product, ProductDataset
from robotoff.utils import get_logger
from robotoff.workers.tasks.import_image import save_image

logger = get_logger()

ds = ProductDataset.load()
saved = 0

seen_set = set(
    (
        (x.barcode, x.image_id)
        for x in ImageModel.select(ImageModel.barcode, ImageModel.image_id).iterator()
    )
)
with db:
    product: Product
    for product in tqdm.tqdm(
        ds.stream().filter_nonempty_text_field("code").iter_product()
    ):
        if product.barcode is None:
            continue

        for image_id in product.images.keys():
            if not image_id.isdigit():
                continue

            if (str(product.barcode), str(image_id)) in seen_set:
                continue

            image_url = generate_image_url(product.barcode, str(image_id))

            try:
                save_image(
                    product.barcode, image_url, product, settings.OFF_SERVER_DOMAIN
                )
            except Exception as e:
                logger.info("Exception for product {}\n{}".format(product.barcode, e))

            saved += 1

logger.info("{} image saved".format(saved))
