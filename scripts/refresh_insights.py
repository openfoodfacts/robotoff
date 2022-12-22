import tqdm
from more_itertools import chunked

from robotoff import settings
from robotoff.insights.importer import refresh_insights
from robotoff.models import ProductInsight, db
from robotoff.utils import get_logger

logger = get_logger()
logger.info("Refreshing insights of all products")

imported = 0

with db:
    barcodes = [
        barcode
        for (barcode, _) in ProductInsight.select(
            ProductInsight.barcode, ProductInsight.timestamp
        )
        .where(ProductInsight.annotation.is_null())
        .order_by(ProductInsight.timestamp.asc(), ProductInsight.barcode.asc())
        .tuples()
        .iterator()
    ]

barcodes = sorted(set(barcodes), key=lambda x: barcodes.index(x))
logger.info(f"{len(barcodes)} products to refresh")
for barcode_batch in tqdm.tqdm(chunked(barcodes, 100)):
    with db:
        for barcode in barcode_batch:
            logger.info(f"Refreshing insights for product {barcode}")
            imported += refresh_insights(barcode, settings.OFF_SERVER_DOMAIN)

logger.info(f"Refreshed insights: {imported}")
