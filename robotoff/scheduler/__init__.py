import datetime
import functools
import os
import uuid
from typing import Dict, Iterable, Optional

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

from robotoff import slack, settings
from robotoff.app.core import get_insights
from robotoff.elasticsearch.category.predict import predict_from_dataset
from robotoff.insights.annotate import (
    InsightAnnotatorFactory,
    UPDATED_ANNOTATION_RESULT,
)
from robotoff.insights.importer import CategoryImporter
from robotoff.insights.validator import (
    InsightValidator,
    InsightValidatorFactory,
    delete_invalid_insight,
)
from robotoff.metrics import save_facet_metrics
from robotoff.models import db, LatentProductInsight, ProductInsight
from robotoff.products import (
    is_valid_image,
    has_dataset_changed,
    fetch_dataset,
    CACHED_PRODUCT_STORE,
    Product,
    ProductStore,
    ProductDataset,
)
from .latent import generate_quality_facets
from robotoff.utils import get_logger, dump_jsonl

import sentry_sdk
from sentry_sdk import capture_exception

if settings.SENTRY_DSN:
    sentry_sdk.init(settings.SENTRY_DSN)


logger = get_logger(__name__)


def process_insights():
    processed = 0
    with db:
        for insight in (
            ProductInsight.select()
            .where(
                ProductInsight.annotation.is_null(),
                ProductInsight.process_after.is_null(False),
                ProductInsight.process_after <= datetime.datetime.utcnow(),
            )
            .iterator()
        ):
            annotator = InsightAnnotatorFactory.get(insight.type)
            logger.info(
                "Annotating insight {} (product: {})".format(
                    insight.id, insight.barcode
                )
            )
            annotation_result = annotator.annotate(insight, 1, update=True)
            processed += 1

            if annotation_result == UPDATED_ANNOTATION_RESULT and insight.data.get(
                "notify", False
            ):
                slack.notify_automatic_processing(insight)

    logger.info("{} insights processed".format(processed))


def refresh_insights(with_deletion: bool = False):
    deleted = 0
    updated = 0
    product_store = CACHED_PRODUCT_STORE.get()

    datetime_threshold = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    dataset_datetime = datetime.datetime.fromtimestamp(
        os.path.getmtime(settings.JSONL_MIN_DATASET_PATH)
    )

    if dataset_datetime.date() != datetime_threshold.date():
        logger.warn("Dataset version is not up to date, aborting insight removal job")
        return

    validators: Dict[str, Optional[InsightValidator]] = {}

    with db:
        with db.atomic():
            for insight in (
                ProductInsight.select()
                .where(
                    ProductInsight.annotation.is_null(),
                    ProductInsight.timestamp <= datetime_threshold,
                    ProductInsight.server_domain == settings.OFF_SERVER_DOMAIN,
                )
                .iterator()
            ):
                product: Product = product_store[insight.barcode]

                if product is None:
                    if with_deletion:
                        # Product has been deleted from OFF
                        logger.info(
                            "Product with barcode {} deleted".format(insight.barcode)
                        )
                        deleted += 1
                        insight.delete_instance()
                else:
                    if insight.type not in validators:
                        validators[insight.type] = InsightValidatorFactory.create(
                            insight.type, product_store
                        )

                    validator = validators[insight.type]
                    insight_deleted = delete_invalid_insight(insight, validator)

                    if insight_deleted:
                        deleted += 1
                        logger.info(
                            "invalid insight {} (type: {}), deleting..."
                            "".format(insight.id, insight.type)
                        )
                        continue

                    insight_updated = update_insight_attributes(product, insight)

                    if insight_updated:
                        updated += 1

    logger.info("{} insights deleted".format(deleted))
    logger.info("{} insights updated".format(updated))


def update_insight_attributes(product: Product, insight: ProductInsight) -> bool:
    to_update = False
    if insight.brands != product.brands_tags:
        logger.info(
            "Updating brand {} -> {} ({})".format(
                insight.brands, product.brands_tags, product.barcode
            )
        )
        to_update = True
        insight.brands = product.brands_tags

    if insight.countries != product.countries_tags:
        logger.info(
            "Updating countries {} -> {} ({})".format(
                insight.countries, product.countries_tags, product.barcode
            )
        )
        to_update = True
        insight.countries = product.countries_tags

    if insight.unique_scans_n != product.unique_scans_n:
        logger.info(
            "Updating unique scan count {} -> {} ({})".format(
                insight.unique_scans_n, product.unique_scans_n, product.barcode
            )
        )
        to_update = True
        insight.unique_scans_n = product.unique_scans_n

    if to_update:
        insight.save()

    return to_update


def mark_insights():
    marked = 0
    with db:
        with db.atomic():
            for insight in (
                ProductInsight.select()
                .where(
                    ProductInsight.automatic_processing == True,  # noqa: E712
                    ProductInsight.process_after.is_null(),
                    ProductInsight.annotation.is_null(),
                )
                .iterator()
            ):
                logger.info(
                    "Marking insight {} as processable automatically "
                    "(product: {})".format(insight.id, insight.barcode)
                )
                insight.process_after = datetime.datetime.utcnow() + datetime.timedelta(
                    minutes=10
                )
                insight.save()
                marked += 1

    logger.info("{} insights marked".format(marked))


def download_product_dataset():
    logger.info("Downloading new version of product dataset")

    if has_dataset_changed():
        fetch_dataset()


def generate_insights():
    """Generate and import category insights from the latest dataset dump, for
    products added at day-1."""
    logger.info("Generating new category insights")
    product_store: ProductStore = CACHED_PRODUCT_STORE.get()
    importer = CategoryImporter(product_store)

    datetime_threshold = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - datetime.timedelta(days=1)
    dataset = ProductDataset(settings.JSONL_DATASET_PATH)
    category_insights_iter = predict_from_dataset(dataset, datetime_threshold)

    imported = importer.import_insights(
        category_insights_iter,
        server_domain=settings.OFF_SERVER_DOMAIN,
        automatic=False,
        latent=False,
    )
    logger.info("{} category insights imported".format(imported))


def transform_insight_iter(insights_iter: Iterable[Dict]):
    for insight in insights_iter:
        for field, value in insight.items():
            if isinstance(value, uuid.UUID):
                insight[field] = str(value)
            elif isinstance(value, datetime.datetime):
                insight[field] = value.isoformat()

        yield insight


def dump_insights():
    logger.info("Dumping insights...")
    insights_iter = get_insights(as_dict=True, annotated=None, limit=None)
    insights_iter = transform_insight_iter(insights_iter)
    dumped = dump_jsonl(settings.INSIGHT_DUMP_PATH, insights_iter)
    logger.info("Dump finished, {} insights dumped".format(dumped))


def delete_invalid_latent_insights():
    logger.info("Deleting invalid latent insights...")

    product_store = CACHED_PRODUCT_STORE.get()
    datetime_threshold = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    dataset_datetime = datetime.datetime.fromtimestamp(
        os.path.getmtime(settings.JSONL_MIN_DATASET_PATH)
    )

    if dataset_datetime.date() != datetime_threshold.date():
        logger.warn(
            "Dataset version is not up to date, aborting latent insight removal job"
        )
        return

    deleted = 0
    for insight in (
        LatentProductInsight.select(
            LatentProductInsight.id,
            LatentProductInsight.barcode,
            LatentProductInsight.source_image,
        )
        .where(
            LatentProductInsight.source_image.is_null(False),
            LatentProductInsight.timestamp <= datetime_threshold,
            ProductInsight.server_domain == settings.OFF_SERVER_DOMAIN,
        )
        .iterator()
    ):
        product = product_store[insight.barcode]
        barcode = insight.barcode
        source_image = insight.source_image

        if not product:
            deleted += 1
            logger.info("Deleted product: {}".format(barcode))
            insight.delete_instance()
        elif (
            product
            and source_image
            and not is_valid_image(product.images, source_image)
        ):
            logger.info(
                "Invalid image for product {}: {} (insight: {})".format(
                    barcode, source_image, insight.id
                )
            )
            deleted += 1
            insight.delete_instance()

    logger.info("Deleted: {}".format(deleted))


def exception_listener(event):
    if event.exception:
        capture_exception(event.exception)


def run():
    scheduler = BlockingScheduler()
    scheduler.add_executor(ThreadPoolExecutor(20))
    scheduler.add_jobstore(MemoryJobStore())
    scheduler.add_job(
        process_insights, "interval", minutes=2, max_instances=1, jitter=20
    )
    scheduler.add_job(mark_insights, "interval", minutes=2, max_instances=1, jitter=20)
    scheduler.add_job(
        dump_insights, "cron", day="*", hour=0, minute=15, max_instances=1
    )
    scheduler.add_job(save_facet_metrics, "cron", day="*", hour=1, max_instances=1)
    scheduler.add_job(
        download_product_dataset, "cron", day="*", hour="3", max_instances=1
    )
    scheduler.add_job(
        functools.partial(refresh_insights, with_deletion=True),
        "cron",
        day="*",
        hour="4",
        max_instances=1,
    )
    scheduler.add_job(
        generate_insights, "cron", day="*", hour="4", minute=15, max_instances=1
    )
    scheduler.add_job(
        delete_invalid_latent_insights,
        "cron",
        day="*",
        hour=4,
        minute=45,
        max_instances=1,
    )
    scheduler.add_job(
        generate_quality_facets, "cron", day="*", hour="5", minute=25, max_instances=1,
    )
    scheduler.add_listener(exception_listener, EVENT_JOB_ERROR)
    scheduler.start()
