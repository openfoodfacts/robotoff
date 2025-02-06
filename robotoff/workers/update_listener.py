from openfoodfacts import Environment, Flavor
from openfoodfacts.images import generate_image_url, generate_json_ocr_url
from openfoodfacts.redis import RedisUpdate
from openfoodfacts.redis import UpdateListener as BaseUpdateListener
from redis import Redis

from robotoff import settings
from robotoff.types import ProductIdentifier, ServerType
from robotoff.utils.logger import get_logger
from robotoff.workers.queues import enqueue_in_job, enqueue_job, get_high_queue, get_low_queue
from robotoff.workers.tasks import delete_product_insights_job
from robotoff.workers.tasks.import_image import run_import_image_job
from robotoff.workers.tasks.product_updated import update_insights_job

logger = get_logger(__name__)


def get_redis_client():
    """Get the Redis client where Product Opener publishes its product updates."""
    return Redis(
        host=settings.REDIS_UPDATE_HOST,
        port=settings.REDIS_UPDATE_PORT,
        decode_responses=True,
    )


class UpdateListener(BaseUpdateListener):
    def process_redis_update(self, redis_update: RedisUpdate):
        logger.debug("New update: %s", redis_update)

        if redis_update.product_type is None:
            logger.warning("Product type is null, skipping")
            return

        action = redis_update.action
        server_type = ServerType.from_product_type(redis_update.product_type)
        product_id = ProductIdentifier(redis_update.code, server_type)

        # Check if the update was triggered by scanbot or specific mass update accounts
        is_scanbot_or_mass_update = redis_update.triggered_by in ["scanbot", "mass_update_account_1", "mass_update_account_2"]

        # Select queue based on triggering actor
        selected_queue = get_low_queue(product_id) if is_scanbot_or_mass_update else get_high_queue(product_id)

        if action == "deleted":
            logger.info("Product %s has been deleted", redis_update.code)
            enqueue_job(
                delete_product_insights_job,
                selected_queue,
                job_kwargs={"result_ttl": 0},
                product_id=product_id,
            )
        elif action == "updated":
            if redis_update.is_image_upload():
                # A new image was uploaded
                image_id = redis_update.diffs["uploaded_images"]["add"][0]  # type: ignore
                logger.info(
                    "Image %s was added on product %s", image_id, redis_update.code
                )
                environment = (
                    Environment.org if settings._get_tld() == "org" else Environment.net
                )
                flavor = Flavor[server_type.name]
                image_url = generate_image_url(
                    redis_update.code,
                    image_id,
                    flavor=flavor,
                    environment=environment,
                )
                ocr_url = generate_json_ocr_url(
                    redis_update.code,
                    image_id,
                    flavor=flavor,
                    environment=environment,
                )
                enqueue_job(
                    run_import_image_job,
                    selected_queue,
                    job_kwargs={"result_ttl": 0},
                    product_id=product_id,
                    image_url=image_url,
                    ocr_url=ocr_url,
                )
            else:
                logger.info("Product %s has been updated", redis_update.code)
                enqueue_in_job(
                    update_insights_job,
                    selected_queue,
                    settings.UPDATED_PRODUCT_WAIT,
                    job_kwargs={"result_ttl": 0},
                    product_id=product_id,
                    diffs=redis_update.diffs,
                )


def run_update_listener():
    """Run the update import daemon.

    This daemon listens to the Redis stream containing information about
    product updates and triggers appropriate actions.
    """
    redis_client = get_redis_client()
    update_listener = UpdateListener(
        redis_client=redis_client,
        redis_stream_name=settings.REDIS_STREAM_NAME,
        redis_latest_id_key=settings.REDIS_LATEST_ID_KEY,
    )
    update_listener.run()
