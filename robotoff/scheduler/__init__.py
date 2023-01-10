import datetime
import functools
import os
import uuid
from typing import Iterable

import requests.exceptions
from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.blocking import BlockingScheduler
from sentry_sdk import capture_exception

from robotoff import settings, slack
from robotoff.elasticsearch import get_es_client
from robotoff.elasticsearch.export import ElasticsearchExporter
from robotoff.insights.annotate import UPDATED_ANNOTATION_RESULT, annotate
from robotoff.insights.importer import import_insights
from robotoff.metrics import (
    ensure_influx_database,
    save_facet_metrics,
    save_insight_metrics,
)
from robotoff.models import ProductInsight, db, with_db
from robotoff.prediction.category.matcher import predict_from_dataset
from robotoff.products import (
    Product,
    ProductDataset,
    fetch_dataset,
    get_min_product_store,
    has_dataset_changed,
)
from robotoff.utils import get_logger

from .latent import generate_quality_facets

settings.init_sentry()

logger = get_logger(__name__)


# Note: we do not use with_db, for atomicity is handled in annotator
def process_insights():
    with db.connection_context():
        processed = 0
        for insight in (
            ProductInsight.select()
            .where(
                ProductInsight.annotation.is_null(),
                ProductInsight.process_after.is_null(False),
                ProductInsight.process_after <= datetime.datetime.utcnow(),
            )
            .iterator()
        ):
            try:
                logger.info(
                    "Annotating insight %s (product: %s)", insight.id, insight.barcode
                )
                annotation_result = annotate(insight, 1, update=True)
                processed += 1

                if annotation_result == UPDATED_ANNOTATION_RESULT and insight.data.get(
                    "notify", False
                ):
                    slack.NotifierFactory.get_notifier().notify_automatic_processing(
                        insight
                    )
            except Exception as e:
                # continue to the next one
                # Note: annotator already rolled-back the transaction
                logger.exception(
                    f"exception {e} while handling annotation of insight %s (product) %s",
                    insight.id,
                    insight.barcode,
                )
    logger.info("%d insights processed", processed)


@with_db
def refresh_insights(with_deletion: bool = False):
    deleted = 0
    updated = 0
    product_store = get_min_product_store()

    datetime_threshold = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    dataset_datetime = datetime.datetime.fromtimestamp(
        os.path.getmtime(settings.JSONL_MIN_DATASET_PATH)
    )

    if dataset_datetime.date() != datetime_threshold.date():
        logger.warning(
            "Dataset version is not up to date, aborting insight removal job"
        )
        return

    for insight in (
        ProductInsight.select()
        .where(
            ProductInsight.annotation.is_null(),
            ProductInsight.timestamp <= datetime_threshold,
            ProductInsight.server_domain == settings.BaseURLProvider.server_domain(),
        )
        .iterator()
    ):
        product: Product = product_store[insight.barcode]

        if product is None:
            if with_deletion:
                # Product has been deleted from OFF
                logger.info("Product with barcode {} deleted".format(insight.barcode))
                deleted += 1
                insight.delete_instance()
        else:
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


@with_db
def mark_insights():
    marked = 0
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
    return marked  # useful for tests


def _download_product_dataset():
    logger.info("Downloading new version of product dataset")

    if has_dataset_changed():
        fetch_dataset()


# this job does no use database
def _update_data():
    """Refreshes the PO product dump and updates the Elasticsearch index data."""
    try:
        _download_product_dataset()
    except requests.exceptions.RequestException:
        logger.exception("Exception during product dataset refresh")

    try:
        ElasticsearchExporter(get_es_client()).load_all_indices()
    except Exception as e:
        logger.exception("Exception during ES indices creation", exc_info=e)


def generate_insights():
    """Generate and import category insights from the latest dataset dump, for
    products added at day-1."""
    logger.info("Generating new category insights")

    datetime_threshold = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - datetime.timedelta(days=1)
    dataset = ProductDataset(settings.JSONL_DATASET_PATH)
    product_predictions_iter = predict_from_dataset(dataset, datetime_threshold)

    with db:
        import_result = import_insights(
            product_predictions_iter,
            server_domain=settings.BaseURLProvider.server_domain(),
        )
    logger.info(import_result)


def transform_insight_iter(insights_iter: Iterable[dict]):
    for insight in insights_iter:
        for field, value in insight.items():
            if isinstance(value, uuid.UUID):
                insight[field] = str(value)
            elif isinstance(value, datetime.datetime):
                insight[field] = value.isoformat()

        yield insight


def exception_listener(event):
    if event.exception:
        capture_exception(event.exception)


# The scheduler is responsible for scheduling periodic work that Robotoff needs to perform.
def run():
    # ensure influxdb database exists
    ensure_influx_database()

    # This call needs to happen on every start of the scheduler to ensure we're not in
    # the state where Robotoff is unable to perform tasks because of missing data.
    _update_data()

    scheduler = BlockingScheduler()
    scheduler.add_executor(ThreadPoolExecutor(20))
    scheduler.add_jobstore(MemoryJobStore())

    # This job takes all of the newly added automatically-processable insights and sets the process_after field on them,
    # indicating when these insights should be auto-applied.
    scheduler.add_job(mark_insights, "interval", minutes=2, max_instances=1, jitter=20)

    # This job applies all of the automatically-processable insights that have not been applied yet.
    scheduler.add_job(
        process_insights, "interval", minutes=2, max_instances=1, jitter=20
    )

    # This job exports daily product metrics for monitoring.
    scheduler.add_job(save_facet_metrics, "cron", day="*", hour=1, max_instances=1)
    scheduler.add_job(save_insight_metrics, "cron", day="*", hour=1, max_instances=1)

    # This job refreshes data needed to generate insights.
    scheduler.add_job(_update_data, "cron", day="*", hour="3", max_instances=1)

    # This job updates the product insights state with respect to the latest PO dump by:
    # - Deleting non-annotated insights for deleted products and insights that
    #   are no longer applicable.
    # - Updating insight attributes.
    scheduler.add_job(
        functools.partial(refresh_insights, with_deletion=True),
        "cron",
        day="*",
        hour="4",
        max_instances=1,
    )

    # This job generates category insights using ElasticSearch from the last Product Opener data dump.
    scheduler.add_job(
        generate_insights, "cron", day="*", hour="4", minute=15, max_instances=1
    )

    scheduler.add_job(
        generate_quality_facets,
        "cron",
        day="*",
        hour="5",
        minute=25,
        max_instances=1,
    )

    scheduler.add_listener(exception_listener, EVENT_JOB_ERROR)
    scheduler.start()
