import datetime

from openfoodfacts.redis import OCRReadyEvent, ProductUpdateEvent
from rq.queue import Queue

from robotoff import settings
from robotoff.types import ImportImageFlag, JSONType, ProductIdentifier, ServerType
from robotoff.workers.tasks import delete_product_insights_job
from robotoff.workers.tasks.import_image import run_import_image_job
from robotoff.workers.tasks.product_updated import (
    deleted_image_job,
    update_insights_job,
)
from robotoff.workers.update_listener import UpdateListener

REDIS_LATEST_ID_KEY = "robotoff:product_updates:latest_id"


def create_product_update_event(
    user_id: str = "test_user",
    comment: str = "Test update",
    action: str = "updated",
    diffs: JSONType | None = None,
) -> ProductUpdateEvent:
    return ProductUpdateEvent(
        id="1234567890-0",
        stream=settings.PRODUCT_UDPATE_STREAM_NAME,
        timestamp=datetime.datetime.now(),
        code="1234567890123",
        flavor="off",
        user_id=user_id,
        action=action,
        product_type="food",
        comment=comment,
        diffs=diffs,
    )


def create_ocr_ready_event(image_id: str) -> OCRReadyEvent:
    return OCRReadyEvent(
        id="1234567890-0",
        stream=settings.OCR_READY_STREAM_NAME,
        timestamp=datetime.datetime.now(),
        code="1234567890123",
        product_type="food",
        image_id=image_id,
        json_url=f"https://images.openfoodfacts.net/images/products/123/456/789/0123/{image_id}.json",
    )


class TestUpdateListener:
    def test_update_listener_update(self, mocker):
        enqueue_in_job = mocker.patch("robotoff.workers.update_listener.enqueue_in_job")
        enqueue_job = mocker.patch("robotoff.workers.update_listener.enqueue_job")
        update_listener = UpdateListener(
            redis_client=None,
            redis_latest_id_key=REDIS_LATEST_ID_KEY,
        )
        redis_update = create_product_update_event()
        update_listener.process_redis_update(redis_update)
        assert enqueue_in_job.call_count == 1
        assert enqueue_job.call_count == 0
        assert len(enqueue_in_job.call_args.args) == 0
        kwargs = enqueue_in_job.call_args.kwargs
        assert set(kwargs.keys()) == {
            "func",
            "queue",
            "job_delay",
            "job_kwargs",
            "product_id",
            "diffs",
        }
        assert kwargs["func"] == update_insights_job
        assert isinstance(kwargs["queue"], Queue)
        assert kwargs["job_delay"] == 10.0
        assert kwargs["job_kwargs"] == {"result_ttl": 0}
        assert kwargs["product_id"] == ProductIdentifier(
            redis_update.code, ServerType[redis_update.flavor]
        )
        assert kwargs["diffs"] is None

    def test_update_listener_update_by_scanbot(self, mocker):
        enqueue_in_job = mocker.patch("robotoff.workers.update_listener.enqueue_in_job")
        enqueue_job = mocker.patch("robotoff.workers.update_listener.enqueue_job")
        update_listener = UpdateListener(
            redis_client=None,
            redis_latest_id_key=REDIS_LATEST_ID_KEY,
        )
        redis_update = create_product_update_event(user_id="scanbot")
        update_listener.process_redis_update(redis_update)
        assert enqueue_in_job.call_count == 1
        assert enqueue_job.call_count == 0
        assert len(enqueue_in_job.call_args.args) == 0
        kwargs = enqueue_in_job.call_args.kwargs
        assert set(kwargs.keys()) == {
            "func",
            "queue",
            "job_delay",
            "job_kwargs",
            "product_id",
            "diffs",
        }
        assert isinstance(kwargs["queue"], Queue)
        # Assert that the queue is the low-priority queue
        assert kwargs["queue"].name == "robotoff-low"

    def test_update_listener_robotoff_update(self, mocker):
        enqueue_in_job = mocker.patch("robotoff.workers.update_listener.enqueue_in_job")
        enqueue_job = mocker.patch("robotoff.workers.update_listener.enqueue_job")
        update_listener = UpdateListener(
            redis_client=None,
            redis_latest_id_key=REDIS_LATEST_ID_KEY,
        )
        redis_update_by_robotoff = create_product_update_event(user_id="roboto-app")
        update_listener.process_redis_update(redis_update_by_robotoff)
        assert enqueue_in_job.call_count == 0
        assert enqueue_job.call_count == 0

        redis_update_by_user_through_robotoff = create_product_update_event(
            comment="[robotoff] Test update"
        )
        update_listener.process_redis_update(redis_update_by_user_through_robotoff)
        assert enqueue_in_job.call_count == 0
        assert enqueue_job.call_count == 0

    def test_update_listener_deleted(self, mocker):
        enqueue_in_job = mocker.patch("robotoff.workers.update_listener.enqueue_in_job")
        enqueue_job = mocker.patch("robotoff.workers.update_listener.enqueue_job")
        update_listener = UpdateListener(
            redis_client=None,
            redis_latest_id_key=REDIS_LATEST_ID_KEY,
        )
        redis_update = create_product_update_event(action="deleted")
        update_listener.process_redis_update(redis_update)
        assert enqueue_in_job.call_count == 0
        assert enqueue_job.call_count == 1
        assert len(enqueue_job.call_args.args) == 0
        kwargs = enqueue_job.call_args.kwargs
        assert set(kwargs.keys()) == {
            "func",
            "queue",
            "job_kwargs",
            "product_id",
        }
        assert kwargs["func"] == delete_product_insights_job
        assert isinstance(kwargs["queue"], Queue)
        assert kwargs["job_kwargs"] == {"result_ttl": 0}
        assert kwargs["product_id"] == ProductIdentifier(
            redis_update.code, ServerType[redis_update.flavor]
        )

    def test_update_listener_image_upload(self, mocker):
        enqueue_in_job = mocker.patch("robotoff.workers.update_listener.enqueue_in_job")
        enqueue_job = mocker.patch("robotoff.workers.update_listener.enqueue_job")
        update_listener = UpdateListener(
            redis_client=None,
            redis_latest_id_key=REDIS_LATEST_ID_KEY,
        )
        redis_update = create_product_update_event(
            diffs='{"uploaded_images": {"add": ["1"]}}'
        )
        update_listener.process_redis_update(redis_update)
        assert enqueue_in_job.call_count == 0
        assert enqueue_job.call_count == 1
        assert len(enqueue_job.call_args.args) == 0
        kwargs = enqueue_job.call_args.kwargs
        assert set(kwargs.keys()) == {
            "func",
            "queue",
            "job_kwargs",
            "product_id",
            "image_url",
            "ocr_url",
            "exclude_flags",
        }
        assert kwargs["func"] == run_import_image_job
        assert isinstance(kwargs["queue"], Queue)
        assert kwargs["job_kwargs"] == {"result_ttl": 0}
        assert kwargs["product_id"] == ProductIdentifier(
            redis_update.code, ServerType[redis_update.flavor]
        )
        assert kwargs["image_url"] == (
            "https://images.openfoodfacts.net/images/products/123/456/789/0123/1.jpg"
        )
        assert kwargs["ocr_url"] == (
            "https://images.openfoodfacts.net/images/products/123/456/789/0123/1.json"
        )
        assert kwargs["exclude_flags"] == [
            ImportImageFlag.extract_ingredients,
            ImportImageFlag.extract_nutrition,
            ImportImageFlag.predict_category,
            ImportImageFlag.import_insights_from_image,
            ImportImageFlag.run_logo_object_detection,
        ]

    def test_update_listener_image_deletion(self, mocker):
        enqueue_in_job = mocker.patch("robotoff.workers.update_listener.enqueue_in_job")
        enqueue_job = mocker.patch("robotoff.workers.update_listener.enqueue_job")
        update_listener = UpdateListener(
            redis_client=None,
            redis_latest_id_key=REDIS_LATEST_ID_KEY,
        )
        redis_update = create_product_update_event(
            diffs='{"uploaded_images": {"delete": ["4"]}}'
        )
        update_listener.process_redis_update(redis_update)
        assert enqueue_in_job.call_count == 1
        assert enqueue_job.call_count == 0
        assert len(enqueue_in_job.call_args.args) == 0
        kwargs = enqueue_in_job.call_args.kwargs
        assert set(kwargs.keys()) == {
            "func",
            "queue",
            "job_kwargs",
            "job_delay",
            "product_id",
            "image_id",
        }
        assert kwargs["func"] == deleted_image_job
        assert isinstance(kwargs["queue"], Queue)
        assert kwargs["job_kwargs"] == {"result_ttl": 0}
        assert kwargs["product_id"] == ProductIdentifier(
            redis_update.code, ServerType[redis_update.flavor]
        )
        assert kwargs["image_id"] == "4"

    def test_update_listener_ocr_ready(self, mocker):
        enqueue_in_job = mocker.patch("robotoff.workers.update_listener.enqueue_in_job")
        enqueue_job = mocker.patch("robotoff.workers.update_listener.enqueue_job")
        update_listener = UpdateListener(
            redis_client=None,
            redis_latest_id_key=REDIS_LATEST_ID_KEY,
        )
        event = create_ocr_ready_event(image_id="4")
        update_listener.process_ocr_ready(event)
        assert enqueue_job.call_count == 1
        assert enqueue_in_job.call_count == 0
        assert len(enqueue_job.call_args.args) == 0
        kwargs = enqueue_job.call_args.kwargs
        assert set(kwargs.keys()) == {
            "func",
            "queue",
            "job_kwargs",
            "product_id",
            "image_url",
            "ocr_url",
            "include_flags",
        }
        assert kwargs["func"] == run_import_image_job
        assert isinstance(kwargs["queue"], Queue)
        assert kwargs["job_kwargs"] == {"result_ttl": 0}
        assert kwargs["product_id"] == ProductIdentifier(
            event.code, ServerType.from_product_type(event.product_type)
        )
        assert (
            kwargs["image_url"]
            == "https://images.openfoodfacts.net/images/products/123/456/789/0123/4.jpg"
        )
        assert (
            kwargs["ocr_url"]
            == "https://images.openfoodfacts.net/images/products/123/456/789/0123/4.json"
        )
        assert kwargs["include_flags"] == [
            ImportImageFlag.extract_ingredients,
            ImportImageFlag.extract_nutrition,
            ImportImageFlag.predict_category,
            ImportImageFlag.import_insights_from_image,
            ImportImageFlag.run_logo_object_detection,
        ]
