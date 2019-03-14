import datetime
import os
from typing import Dict, Set

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

from robotoff import slack, settings
from robotoff.insights._enum import InsightType
from robotoff.insights.annotate import InsightAnnotatorFactory, UPDATED_ANNOTATION_RESULT
from robotoff.insights.importer import InsightImporterFactory, InsightImporter
from robotoff.models import ProductInsight, db
from robotoff.products import has_dataset_changed, fetch_dataset, \
    CACHED_PRODUCT_STORE
from robotoff.utils import get_logger

import sentry_sdk
from sentry_sdk import capture_exception

if settings.SENTRY_DSN:
    sentry_sdk.init(settings.SENTRY_DSN)


logger = get_logger(__name__)

NEED_VALIDATION_INSIGHTS: Set[str] = set()


def process_insights():
    processed = 0
    with db:
        with db.atomic():
            for insight in (ProductInsight.select()
                                          .where(ProductInsight.annotation.is_null(),
                                                 ProductInsight.outdated == False,
                                                 ProductInsight.process_after.is_null(False),
                                                 ProductInsight.process_after <= datetime.datetime.utcnow())
                                          .iterator()):
                insight.annotation = 1
                insight.completed_at = datetime.datetime.utcnow()
                insight.save()

                annotator = InsightAnnotatorFactory.get(insight.type)
                logger.info("Annotating insight {} (product: {})".format(insight.id, insight.barcode))
                annotation_result = annotator.annotate(insight, 1, update=True)
                processed += 1

                if processed < 20 and annotation_result == UPDATED_ANNOTATION_RESULT:
                    slack.notify_automatic_processing(insight)

    if processed > 20:
        slack.notify_batch_processing(processed - 20)

    logger.info("{} insights processed".format(processed))


def remove_invalid_insights():
    deleted = 0
    product_store = CACHED_PRODUCT_STORE.get()

    datetime_threshold = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0)
    dataset_datetime = datetime.datetime.fromtimestamp(
        os.path.getmtime(settings.JSONL_MIN_DATASET_PATH))

    if dataset_datetime.date() != datetime_threshold.date():
        logger.warn("Dataset version is not up to date, aborting insight "
                    "removal job")
        return

    with db:
        with db.atomic():
            for insight in (ProductInsight.select()
                    .where(ProductInsight.annotation.is_null(),
                           ProductInsight.timestamp <= datetime_threshold)
                    .iterator()):
                if product_store[insight.barcode] is None:
                    # Product has been deleted from OFF
                    print("Product with barcode {} deleted"
                          "".format(insight.barcode))
                    deleted += 1
                    insight.delete_instance()

    logger.info("{} insights deleted".format(deleted))


def mark_insights():
    importers: Dict[str, InsightImporter] = {
        insight_type.name: InsightImporterFactory.create(insight_type.name,
                                                         None)
        for insight_type in InsightType
        if insight_type.name in InsightImporterFactory.importers
    }

    marked = 0
    with db:
        with db.atomic():
            for insight in (ProductInsight.select()
                                          .where(ProductInsight.process_after.is_null(),
                                                 ProductInsight.annotation.is_null(),
                                                 ProductInsight.outdated == False)
                                          .iterator()):
                if insight.id in NEED_VALIDATION_INSIGHTS:
                    continue

                importer = importers.get(insight.type)

                if importer is None:
                    continue

                if not importer.need_validation(insight):
                    logger.info("Marking insight {} as processable automatically "
                                "(product: {})".format(insight.id, insight.barcode))
                    insight.process_after = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
                    insight.save()
                    marked += 1
                else:
                    NEED_VALIDATION_INSIGHTS.add(insight.id)

    logger.info("{} insights marked".format(marked))


def download_product_dataset():
    logger.info("Downloading new version of product dataset")

    if has_dataset_changed():
        fetch_dataset()


def exception_listener(event):
    if event.exception:
        capture_exception(event.exception)


def run():
    scheduler = BlockingScheduler()
    scheduler.add_executor(ThreadPoolExecutor(20))
    scheduler.add_jobstore(MemoryJobStore())
    scheduler.add_job(process_insights, 'interval', minutes=2, max_instances=1, jitter=20)
    scheduler.add_job(mark_insights, 'interval', minutes=2, max_instances=1, jitter=20)
    scheduler.add_job(download_product_dataset, 'cron', day='*', hour='3', max_instances=1)
    scheduler.add_job(remove_invalid_insights, 'cron', day='*', hour='4', max_instances=1)
    scheduler.add_listener(exception_listener, EVENT_JOB_ERROR)
    scheduler.start()
