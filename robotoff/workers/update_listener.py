import datetime

from openfoodfacts import Environment, Flavor
from openfoodfacts.images import generate_image_url, generate_json_ocr_url
from openfoodfacts.redis import RedisUpdate, get_new_updates, get_processed_since
from redis import Redis

from robotoff import settings
from robotoff.types import ProductIdentifier, ServerType
from robotoff.utils.logger import get_logger
from robotoff.workers.queues import enqueue_in_job, enqueue_job, get_high_queue
from robotoff.workers.tasks import delete_product_insights_job
from robotoff.workers.tasks.import_image import run_import_image_job
from robotoff.workers.tasks.product_updated import update_insights_job

logger = get_logger(__name__)


def get_redis_client():
    """Get the Redis client where Product Opener publishes it's product
    update."""
    return Redis(
        host=settings.REDIS_UPDATE_HOST,
        port=settings.REDIS_UPDATE_PORT,
        decode_responses=True,
    )


def run_update_listener():
    """Run the update import daemon.

    This daemon listens to the Redis stream containing information about
    product updates, and triggers
    """
    logger.info("Starting update listener daemon")

    client = get_redis_client()
    logger.info("Redis client: %s", client)
    logger.info("Pinging client...")
    client.ping()
    logger.info("Connection successful")
    redis_latest_id_key = "robotoff:product_updates:latest_id"

    latest_id = client.get(redis_latest_id_key)

    if latest_id:
        logger.info(
            "Latest ID processed: %s (datetime: %s)",
            latest_id,
            datetime.datetime.fromtimestamp(int(latest_id.split("-")[0]) / 1000),
        )
    else:
        logger.info("No latest ID found")

    for redis_update in get_new_updates(
        client, stream_name=settings.REDIS_STREAM_NAME, min_id=latest_id
    ):
        process_redis_update(redis_update)
        client.set(redis_latest_id_key, redis_update.id)


def process_updates_since(
    since: datetime.datetime, to: datetime.datetime | None = None
):
    """Process all the updates since the given timestamp.

    :param client: the Redis client
    :param since: the timestamp to start from
    :param to: the timestamp to stop, defaults to None (process all updates)
    """
    client = get_redis_client()
    logger.info("Redis client: %s", client)
    logger.info("Pinging client...")
    client.ping()

    processed = 0
    for product_update in get_processed_since(
        client, stream_name=settings.REDIS_STREAM_NAME, min_id=since
    ):
        if to is not None and product_update.timestamp > to:
            break
        process_redis_update(product_update)
        processed += 1

    logger.info("Processed %d updates", processed)


def process_redis_update(redis_update: RedisUpdate):
    logger.debug("New update: %s", redis_update)
    action = redis_update.action
    product_id = ProductIdentifier(redis_update.code, ServerType[redis_update.flavor])
    if action == "deleted":
        logger.info("Product %s has been deleted", redis_update.code)
        enqueue_job(
            delete_product_insights_job,
            get_high_queue(product_id),
            job_kwargs={"result_ttl": 0},
            product_id=product_id,
        )
    elif action == "updated":
        if redis_update.is_image_upload():
            # A new image was uploaded
            image_id = redis_update.diffs["uploaded_images"]["add"][0]  # type: ignore
            logger.info("Image %s was added on product %s", image_id, redis_update.code)
            environment = (
                Environment.org if settings._get_tld() == "org" else Environment.net
            )
            image_url = generate_image_url(
                redis_update.code,
                image_id,
                flavor=Flavor[redis_update.flavor],
                environment=environment,
            )
            ocr_url = generate_json_ocr_url(
                redis_update.code,
                image_id,
                flavor=Flavor[redis_update.flavor],
                environment=environment,
            )
            enqueue_job(
                run_import_image_job,
                get_high_queue(product_id),
                job_kwargs={"result_ttl": 0},
                product_id=product_id,
                image_url=image_url,
                ocr_url=ocr_url,
            )
        else:
            logger.info("Product %s has been updated", redis_update.code)
            enqueue_in_job(
                update_insights_job,
                get_high_queue(product_id),
                settings.UPDATED_PRODUCT_WAIT,
                job_kwargs={"result_ttl": 0},
                product_id=product_id,
                diffs=redis_update.diffs,
            )
