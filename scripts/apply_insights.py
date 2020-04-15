import argparse
import datetime
import pathlib
from typing import Dict, Optional

from peewee import fn

from robotoff.insights._enum import InsightType
from robotoff.insights.annotate import InsightAnnotatorFactory
from robotoff.insights.data import AUTHORIZED_LABELS
from robotoff.models import ProductInsight
from robotoff.off import get_product

from robotoff.utils import get_logger

logger = get_logger()


class InvalidInsight(Exception):
    pass


def is_automatically_processable(
    insight: ProductInsight, max_timedelta: datetime.timedelta
) -> bool:
    if not insight.source_image:
        return False

    image_path = pathlib.Path(insight.source_image)
    image_id = image_path.stem

    if not image_id.isdigit():
        return False

    product = get_product(insight.barcode, fields=["images"])

    if product is None:
        logger.info("Missing product: {}".format(insight.barcode))
        raise InvalidInsight()

    if "images" not in product:
        logger.info("No images for product {}".format(insight.barcode))
        raise InvalidInsight()

    product_images = product["images"]

    if image_id not in product_images:
        logger.info(
            "Missing image for product {}, ID: {}".format(insight.barcode, image_id)
        )
        raise InvalidInsight()

    if is_recent_image(product_images, image_id, max_timedelta):
        return True

    if is_selected_image(product_images, image_id):
        return True

    return False


def is_selected_image(product_images: Dict, image_id: str) -> bool:
    for key_prefix in ("nutrition", "front", "ingredients"):
        for key, image in product_images.items():
            if key.startswith(key_prefix):
                if image["imgid"] == image_id:
                    logger.info(
                        "Image {} is a selected image for "
                        "'{}'".format(image_id, key_prefix)
                    )
                    return True

    return False


def is_recent_image(
    product_images: Dict, image_id: str, max_timedelta: datetime.timedelta
) -> bool:
    upload_datetimes = []
    insight_image_upload_datetime: Optional[datetime.datetime] = None

    for key, image_meta in product_images.items():
        if not key.isdigit():
            continue

        upload_datetime = datetime.datetime.utcfromtimestamp(
            int(image_meta["uploaded_t"])
        )
        if key == image_id:
            insight_image_upload_datetime = upload_datetime
        else:
            upload_datetimes.append(upload_datetime)

    if not upload_datetimes:
        logger.info("No other images")
        return True

    if insight_image_upload_datetime is None:
        raise ValueError("Image with ID {} not found".format(image_id))

    else:
        for upload_datetime in upload_datetimes:
            if upload_datetime - insight_image_upload_datetime > max_timedelta:
                logger.info(
                    "More recent image: {} > {}".format(
                        upload_datetime, insight_image_upload_datetime
                    )
                )
                return False

        sorted_datetimes = [
            str(x)
            for x in sorted(set(x.date() for x in upload_datetimes), reverse=True)
        ]
        logger.info(
            "All images were uploaded the same day or before the target "
            "image:\n{} >= {}".format(
                insight_image_upload_datetime.date(), ", ".join(sorted_datetimes)
            )
        )
        return True

    logger.info(
        "More recent images: {} < {}".format(
            insight_image_upload_datetime.date(),
            max(x.date() for x in upload_datetimes),
        )
    )
    return False


def run(insight_type: str, max_timedelta: datetime.timedelta):
    logger.info("Timedelta: {}".format(max_timedelta))
    count = 0
    insight: ProductInsight

    annotator = InsightAnnotatorFactory.get(insight_type)

    for insight in (
        ProductInsight.select()
        .where(ProductInsight.type == insight_type, ProductInsight.annotation.is_null())
        .order_by(fn.Random())
    ):
        if (
            insight.process_after is not None
            and insight.process_after >= datetime.datetime.utcnow()
        ):
            continue

        if (
            insight_type == InsightType.label.name
            and insight.value_tag not in AUTHORIZED_LABELS
        ):
            continue

        try:
            is_processable = is_automatically_processable(insight, max_timedelta)
        except InvalidInsight:
            logger.info("Deleting insight {}".format(insight.id))
            insight.delete_instance()
            continue

        if is_processable:
            logger.info(
                "Annotating insight {} (barcode: {})".format(
                    insight.value_tag, insight.barcode
                )
            )
            annotator.annotate(insight, 1, update=True)
            count += 1

    logger.info("Annotated insights: {}".format(count))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("insight_type", choices=[x.name for x in InsightType])
    parser.add_argument("--delta", type=int, default=1)
    args = parser.parse_args()
    run(args.insight_type, datetime.timedelta(days=args.delta))
