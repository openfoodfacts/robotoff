import logging

from robotoff.elasticsearch import get_es_client
from robotoff.images import delete_images
from robotoff.insights.extraction import get_predictions_from_product_name
from robotoff.insights.importer import import_insights, refresh_insights
from robotoff.logos import delete_ann_logos
from robotoff.models import (
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    Prediction,
    ProductInsight,
    with_db,
)
from robotoff.off import (
    generate_image_path,
    generate_image_url,
    generate_json_ocr_url,
    get_product_type,
)
from robotoff.products import get_product
from robotoff.redis import Lock, LockedResourceException
from robotoff.types import JSONType, ProductIdentifier, ServerType
from robotoff.workers.queues import enqueue_job, get_high_queue
from robotoff.workers.tasks.common import add_category_insight
from robotoff.workers.tasks.import_image import run_import_image_job

logger = logging.getLogger(__name__)


@with_db
def update_insights_job(
    product_id: ProductIdentifier,
    diffs: JSONType,
    force_category_prediction: bool = False,
) -> None:
    """This job is triggered by the webhook API, when product information has
    been updated.

    When a product is updated, Robotoff will:

    1. Generate new predictions related to the product's category and name.
    2. Regenerate all insights from the product associated predictions.

    :param product_id: identifier of the product
    :param diffs: a dict containing a diff of the update, the format is
        defined by Product Opener
    :param force_category_prediction: if True, the category predictor will
        be rerun even if the diffs do not indicate that it should be rerun.
    """
    logger.info("Running `update_insights` for %s", product_id)

    # Check for valid product identifier
    if not product_id.is_valid():
        logger.info("Invalid product identifier received, skipping product update")
        return

    try:
        with Lock(
            name=f"robotoff:product_update_job:{product_id.server_type.name}:{product_id.barcode}",
            expire=300,
            timeout=10,
        ):
            # We handle concurrency thanks to the lock as the task will fetch
            # product from MongoDB at the time it runs, it's not worth
            # reprocessing with another task arriving concurrently.
            # The expire is there only in case the lock is not released
            # (process killed)
            deleted_images = diffs.get("uploaded_images", {}).get("delete")
            if deleted_images:
                # deleted_images is a list of image IDs that have been deleted
                logger.info("images deleted: %s, launching DB update", deleted_images)
                delete_images(product_id, deleted_images)

            product_dict = get_product(product_id)

            if product_dict is None:
                logger.info("Updated product does not exist: %s", product_id)
                return

            updated_product_predict_insights(
                product_id,
                product_dict,
                diffs=diffs,
                force_category_prediction=force_category_prediction,
            )
            logger.info("Refreshing insights...")
            import_results = refresh_insights(product_id)
            for import_result in import_results:
                logger.info(import_result)
    except LockedResourceException:
        logger.info(
            "Couldn't acquire product_update lock, skipping product_update for product %s",
            product_id,
        )


def should_rerun_category_predictor(diffs: JSONType | None) -> bool:
    """Check if the category predictor should be rerun based on the update diffs.

    :param diffs: a dict containing a diff of the update, the format is
        defined by Product Opener. This is used to determine whether we
        should run the category predictor again or not, depending on the
        changes made to the product.
    :return: True if the category predictor should be rerun, False otherwise.
    """
    if diffs is None:
        return True

    fields_to_check = ["product_name", "ingredients_text"]
    fields = diffs.get("fields", {})
    updated_fields = fields.get("change", [])
    added_fields = fields.get("add", [])
    has_nutriments_change = "nutriments" in diffs
    uploaded_images = diffs.get("uploaded_images", {})
    is_uploaded_image = "add" in uploaded_images
    is_deleted_image = "delete" in uploaded_images
    # Check if any of the fields that affect category prediction have changed
    return (
        has_nutriments_change
        or is_uploaded_image
        or is_deleted_image
        or any(key in updated_fields for key in fields_to_check)
        or any(key in added_fields for key in fields_to_check)
    )


def updated_product_predict_insights(
    product_id: ProductIdentifier,
    product: JSONType,
    triton_uri: str | None = None,
    diffs: JSONType | None = None,
    force_category_prediction: bool = False,
) -> None:
    """Predict and import category insights and insights-derived from product
    name.

    :param product_id: identifier of the product
    :param product: product as retrieved from MongoDB
    :param triton_uri: URI of the Triton Inference Server, defaults to
        None. If not provided, the default value from settings is used.
    :param diffs: a dict containing a diff of the update, the format is
        defined by Product Opener. This is used to determine whether we
        should run the category predictor again or not, depending on the
        changes made to the product.
    :param force_category_prediction: if True, the category predictor will
        be rerun even if the diffs do not indicate that it should be rerun.
    """
    if force_category_prediction or should_rerun_category_predictor(diffs):
        add_category_insight(product_id, product, triton_uri=triton_uri)

    product_name = product.get("product_name")

    if not product_name:
        return

    if product_id.server_type.is_food():
        # Only available for food products for now
        logger.info("Generating predictions from product name...")
        predictions_all = get_predictions_from_product_name(product_id, product_name)
        import_result = import_insights(predictions_all, product_id.server_type)
        logger.info(import_result)


@with_db
def product_type_switched_job(product_id: ProductIdentifier) -> None:
    """This job is triggered when a product type has been switched.

    We delete elements in all tables that are related to the product
    and reimport the images with the new product type.

    More specifically, we delete for the product:
    - all logo annotations, from DB and Elasticsearch
    - all image predictions from DB
    - all images from DB
    - all predictions from DB
    - all non-annotated insights from DB

    We also schedule:
    - the reimport of all images with the new product type
    - the insight update for the product (including the category
      prediction).

    :param product_id: identifier of the product
    """
    new_product_type = get_product_type(product_id)

    if new_product_type is None:
        logger.info(
            "Product %s was not found on any server (off, obf, opf, opff). "
            "Skipping product type switch",
            product_id,
        )
        return

    new_server_type = ServerType.from_product_type(new_product_type)
    new_product_id = ProductIdentifier(
        barcode=product_id.barcode,
        server_type=new_server_type,
    )

    if new_server_type is product_id.server_type:
        logger.info(
            "Product type for %s has not changed, skipping product type switch",
            product_id,
        )
        return

    product_dict = get_product(new_product_id)

    if product_dict is None:
        # This should not happen (unless the product was deleted in the meantime),
        # but we check just in case
        logger.info(
            "Product %s does not exist, skipping product type switch",
            product_id,
        )
        return

    logo_ids = [
        logo_id
        for (logo_id,) in LogoAnnotation.select(LogoAnnotation.id)
        .join(ImagePrediction)
        .join(ImageModel)
        .where(
            ImageModel.barcode == product_id.barcode,
            ImageModel.server_type == product_id.server_type,
        )
        .tuples()
    ]
    deleted_logos_es = 0
    if logo_ids:
        es_client = get_es_client()
        deleted_logos_es = delete_ann_logos(es_client, logo_ids)

    deleted_logos = (
        LogoAnnotation.delete()
        .where(
            LogoAnnotation.id.in_(logo_ids),
        )
        .execute()
    )
    # Delete all prediction and insights related to the product
    deleted_image_predictions = (
        ImagePrediction.delete()
        .where(
            ImagePrediction.image_id
            == (
                ImageModel.select(ImageModel.id).where(
                    ImageModel.barcode == product_id.barcode,
                    ImageModel.server_type == product_id.server_type,
                )
            )
        )
        .execute()
    )
    deleted_images = (
        ImageModel.delete()
        .where(
            ImageModel.barcode == product_id.barcode,
            ImageModel.server_type == product_id.server_type,
        )
        .execute()
    )

    deleted_predictions = (
        Prediction.delete()
        .where(
            Prediction.barcode == product_id.barcode,
            Prediction.server_type == product_id.server_type,
        )
        .execute()
    )
    deleted_insights = (
        ProductInsight.delete()
        .where(
            ProductInsight.barcode == product_id.barcode,
            ProductInsight.server_type == product_id.server_type,
            ProductInsight.annotation.is_null(
                True
            ),  # Only delete insights without annotations
        )
        .execute()
    )

    high_queue = get_high_queue(product_id)
    for image_id in (k for k in product_dict.get("images", {}) if k.isdigit()):
        image_url = generate_image_url(new_product_id, image_id)
        ocr_url = generate_json_ocr_url(new_product_id, image_id)
        # We reimport all images with the new product ID
        enqueue_job(
            func=run_import_image_job,
            queue=high_queue,
            job_kwargs={"result_ttl": 0},
            product_id=new_product_id,
            image_url=image_url,
            ocr_url=ocr_url,
        )

    # Then we launch the job to reprocess insights
    enqueue_job(
        func=update_insights_job,
        queue=high_queue,
        job_kwargs={"result_ttl": 0},
        product_id=new_product_id,
        diffs={},  # No diffs to pass, we just want to reprocess
        force_category_prediction=True,  # Force category prediction as the product type has changed
    )
    logger.info(
        "Product type switched for %s, "
        "deleted %s images, "
        "%d logos, "
        "%d logos on Elasticsearch, "
        "%d image predictions, "
        "%d predictions and "
        "%d insights",
        product_id,
        deleted_images,
        deleted_logos,
        deleted_logos_es,
        deleted_image_predictions,
        deleted_predictions,
        deleted_insights,
    )


@with_db
def deleted_image_job(product_id: ProductIdentifier, image_id: str) -> None:
    """Process the deletion of an image for a product.

    This job is triggered when an image is deleted from a product. We perform the
    following actions:

    1. Delete all logo annotations related to the image, both in DB and Elasticsearch.
    2. Delete all image predictions related to the image.
    3. Set the `deleted` flag to True for this image (in the `image` table).
    4. Delete predictions (all) and insights (only non-annotated) related to the image.

    :param product_id: identifier of the product
    :param image_id: ID of the image to delete (ex: "3")
    """
    image_model = ImageModel.get_or_none(
        ImageModel.barcode == product_id.barcode,
        ImageModel.server_type == product_id.server_type,
        ImageModel.image_id == image_id,
    )
    source_image = generate_image_path(product_id, image_id)
    deleted_logos_es = 0
    deleted_logos = 0
    deleted_image_predictions = 0

    if image_model is not None:
        logo_ids = [
            logo_id
            for (logo_id,) in LogoAnnotation.select(LogoAnnotation.id)
            .join(ImagePrediction)
            .where(ImagePrediction.image == image_model)
            .tuples()
        ]
        if logo_ids:
            es_client = get_es_client()
            deleted_logos_es = delete_ann_logos(es_client, logo_ids)

        deleted_logos = (
            LogoAnnotation.delete()
            .where(
                LogoAnnotation.id.in_(logo_ids),
            )
            .execute()
        )
        # Delete all prediction and insights related to the product
        deleted_image_predictions = (
            ImagePrediction.delete()
            .where(ImagePrediction.image == image_model)
            .execute()
        )
        image_model.deleted = True
        image_model.save()

    deleted_predictions = (
        Prediction.delete()
        .where(
            Prediction.barcode == product_id.barcode,
            Prediction.server_type == product_id.server_type,
            Prediction.source_image == source_image,
        )
        .execute()
    )
    deleted_insights = (
        ProductInsight.delete()
        .where(
            ProductInsight.barcode == product_id.barcode,
            ProductInsight.server_type == product_id.server_type,
            ProductInsight.source_image == source_image,
            ProductInsight.annotation.is_null(
                True
            ),  # Only delete insights without annotations
        )
        .execute()
    )

    logger.info(
        "Image deleted (product: %s, image ID: %s), "
        "%d logo(s), "
        "%d logo(s) on Elasticsearch, "
        "%d image prediction(s), "
        "%d prediction(s) and "
        "%d insight(s)",
        product_id,
        image_id,
        deleted_logos,
        deleted_logos_es,
        deleted_image_predictions,
        deleted_predictions,
        deleted_insights,
    )
