import tqdm

from robotoff.models import ImageModel, db
from robotoff.off import generate_image_path, generate_image_url
from robotoff.products import Product, ProductDataset
from robotoff.types import ProductIdentifier, ServerType
from robotoff.utils import get_logger
from robotoff.workers.tasks.import_image import save_image

logger = get_logger()
SERVER_TYPE = ServerType.off
ds = ProductDataset.load()
saved = 0

seen_set = set(
    (
        (x.barcode, x.image_id)
        for x in ImageModel.select(ImageModel.barcode, ImageModel.image_id)
        .where(ImageModel.server_type == SERVER_TYPE.name)
        .iterator()
    )
)

with db:
    product: Product
    for product in tqdm.tqdm(
        ds.stream().filter_nonempty_text_field("code").iter_product()
    ):
        if product.barcode is None:
            continue

        product_id = ProductIdentifier(product.barcode, SERVER_TYPE)
        for image_id in product.images.keys():
            if not image_id.isdigit():
                continue

            if (str(product.barcode), str(image_id)) in seen_set:
                continue

            source_image = generate_image_path(product.barcode, str(image_id))
            image_url = generate_image_url(product_id, str(image_id))

            try:
                save_image(product_id, source_image, image_url, product.images)
            except Exception as e:
                logger.info("Exception for %s\n%s", product_id, e)

            saved += 1

logger.info("{} image saved".format(saved))
