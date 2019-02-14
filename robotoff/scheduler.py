import datetime

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

from robotoff.insights.annotate import InsightAnnotatorFactory
from robotoff.models import ProductInsight, db
from robotoff.utils import get_logger

logger = get_logger(__name__)


def process_insights():
    with db:
        with db.atomic():
            for insight in (ProductInsight.select()
                                          .where(ProductInsight.process_after.is_null(False),
                                                 ProductInsight.process_after >= datetime.datetime.utcnow())
                                          .iterator()):
                insight.annotation = 1
                insight.completed_at = datetime.datetime.utcnow()
                insight.save()

                annotator = InsightAnnotatorFactory.create(insight.type)
                annotator.annotate(insight, 1, update=True)


def run():
    scheduler = BlockingScheduler()
    scheduler.add_executor(ThreadPoolExecutor(20))
    scheduler.add_jobstore(MemoryJobStore())
    scheduler.add_job(process_insights, 'interval', minutes=2, max_instances=1)
    scheduler.start()
