import logging

import backoff
from openfoodfacts import Flavor
from openfoodfacts.images import generate_image_url, generate_json_ocr_url
from openfoodfacts.redis import OCRReadyEvent, ProductUpdateEvent
from openfoodfacts.redis import UpdateListener as BaseUpdateListener
from redis import Redis
from redis.exceptions import ConnectionError

from robotoff import settings
from robotoff.types import ImportImageFlag, ProductIdentifier, ServerType
from robotoff.workers.queues import (
    enqueue_in_job,
    enqueue_job,
    get_high_queue,
    get_low_queue,
)
from robotoff.workers.tasks import delete_product_insights_job
from robotoff.workers.tasks.import_image import run_import_image_job
from robotoff.workers.tasks.product_updated import (
    deleted_image_job,
    product_type_switched_job,
    update_insights_job,
)

logger = logging.getLogger(__name__)


def get_redis_client():
    """Get the Redis client where Product Opener publishes its product updates."""
    return Redis(
        host=settings.REDIS_UPDATE_HOST,
        port=settings.REDIS_UPDATE_PORT,
        decode_responses=True,
    )


class UpdateListener(BaseUpdateListener):
    def process_redis_update(self, event: ProductUpdateEvent):
        logger.debug("New update: %s", event)

        if event.product_type is None:
            logger.warning("Product type is null, skipping")
            return

        if not event.code:
            logger.warning("Product code is empty or null ('%s'), skipping", event.code)
            return

        action = event.action
        server_type = ServerType.from_product_type(event.product_type)
        product_id = ProductIdentifier(event.code, server_type)

        # Check if the update was triggered by scanbot or specific mass update accounts
        is_scanbot_or_mass_update = event.user_id in [
            "scanbot",
            "update_all_products",
        ]
        # Select queue based on triggering actor
        selected_queue = (
            get_low_queue() if is_scanbot_or_mass_update else get_high_queue(product_id)
        )

        if event.user_id == "roboto-app" or "[robotoff]" in event.comment:
            # If the update was triggered by Robotoff (automatically of through a user
            # annotation), we skip it as the DB is already up to date with respect to
            # Product Opener changes. Besides, it prevents unnecessary processing and
            # race conditions during insight update/deletion.
            logger.info(
                "Skipping update for product %s triggered by Robotoff",
                event.code,
            )
            return

        if action == "deleted":
            logger.info("Product %s has been deleted", event.code)
            enqueue_job(
                func=delete_product_insights_job,
                queue=selected_queue,
                job_kwargs={"result_ttl": 0},
                product_id=product_id,
            )
        elif action == "updated":
            if event.is_image_upload():
                # A new image was uploaded
                image_id = event.diffs["uploaded_images"]["add"][0]  # type: ignore
                logger.info("Image %s was added on product %s", image_id, event.code)
                environment = settings.get_environment()
                flavor = Flavor[server_type.name]
                image_url = generate_image_url(
                    event.code,
                    image_id,
                    flavor=flavor,
                    environment=environment,
                )
                ocr_url = generate_json_ocr_url(
                    event.code,
                    image_id,
                    flavor=flavor,
                    environment=environment,
                )
                enqueue_job(
                    func=run_import_image_job,
                    queue=selected_queue,
                    job_kwargs={"result_ttl": 0},
                    product_id=product_id,
                    image_url=image_url,
                    ocr_url=ocr_url,
                    # Exclude all models that rely on OCR, as OCR may not be ready yet
                    # when the image is uploaded. A separate OCR ready event will be
                    # sent by Product Opener when the OCR processing is done, which will
                    # trigger a separate job to update insights relying on OCR (see
                    # `process_ocr_ready` method below).
                    exclude_flags=[
                        ImportImageFlag.extract_ingredients,
                        ImportImageFlag.extract_nutrition,
                        ImportImageFlag.predict_category,
                        ImportImageFlag.import_insights_from_image,
                        # We extract text from logos, so it requires OCR
                        ImportImageFlag.run_logo_object_detection,
                    ],
                )
            elif event.is_product_type_change():
                logger.info(
                    "Product type has been updated for product %s",
                    event.code,
                )
                enqueue_in_job(
                    func=product_type_switched_job,
                    queue=selected_queue,
                    job_delay=settings.UPDATED_PRODUCT_WAIT,
                    job_kwargs={"result_ttl": 0},
                    product_id=product_id,
                )
            elif event.is_image_deletion():
                image_id = event.diffs["uploaded_images"]["delete"][0]  # type: ignore
                logger.info(
                    "Image %s for product %s has been deleted",
                    image_id,
                    event.code,
                )
                enqueue_in_job(
                    func=deleted_image_job,
                    queue=selected_queue,
                    job_delay=settings.UPDATED_PRODUCT_WAIT,
                    job_kwargs={"result_ttl": 0},
                    product_id=product_id,
                    image_id=image_id,
                )
            else:
                logger.info("Product %s has been updated", event.code)
                enqueue_in_job(
                    func=update_insights_job,
                    queue=selected_queue,
                    job_delay=settings.UPDATED_PRODUCT_WAIT,
                    job_kwargs={"result_ttl": 0},
                    product_id=product_id,
                    diffs=event.diffs,
                )

    def process_ocr_ready(self, event: OCRReadyEvent):
        logger.info("New OCR ready event: %s", event)

        if not event.code:
            logger.warning("Product code is empty or null ('%s'), skipping", event.code)
            return

        if event.image_id is None:
            logger.warning(
                "Image ID is empty or null for product '%s', skipping", event.code
            )
            return

        server_type = ServerType.from_product_type(event.product_type)
        flavor = Flavor[server_type.name]
        product_id = ProductIdentifier(event.code, server_type)

        environment = settings.get_environment()
        image_url = generate_image_url(
            event.code,
            event.image_id,
            flavor=flavor,
            environment=environment,
        )
        ocr_url = generate_json_ocr_url(
            event.code,
            event.image_id,
            flavor=flavor,
            environment=environment,
        )
        selected_queue = get_high_queue(product_id)
        enqueue_job(
            func=run_import_image_job,
            queue=selected_queue,
            job_kwargs={"result_ttl": 0},
            product_id=product_id,
            image_url=image_url,
            ocr_url=ocr_url,
            # Only include models that rely on OCR, as these tasks were not launched
            # when the image was uploaded.
            include_flags=[
                ImportImageFlag.extract_ingredients,
                ImportImageFlag.extract_nutrition,
                ImportImageFlag.predict_category,
                ImportImageFlag.import_insights_from_image,
                # We extract text from logos, so it requires OCR
                ImportImageFlag.run_logo_object_detection,
            ],
        )


@backoff.on_exception(
    backoff.expo,
    ConnectionError,
    max_value=60,  # we wait at most 60 seconds between retries
    jitter=backoff.random_jitter,
    on_backoff=lambda details: logger.error(
        "Redis connection error (attempt %d): %s. Retrying in %.1f seconds...",
        details["tries"],
        details["exception"],
        details["wait"],
    ),
    on_giveup=lambda details: logger.critical(
        "Max retries (%d) reached. Update listener is terminating.", details["tries"]
    ),
)
def run_update_listener():
    """Run the update import daemon.

    This daemon listens to the Redis stream containing information about
    product updates and triggers appropriate actions.
    """
    logger.info("Starting Redis update listener...")
    while True:
        try:
            redis_client = get_redis_client()
            update_listener = UpdateListener(
                redis_client=redis_client,
                redis_latest_id_key=settings.REDIS_LATEST_ID_KEY,
            )
            update_listener.run()
        except Exception as e:
            logger.critical(
                "Unexpected error in update listener: %s", str(e), exc_info=True
            )
            raise
