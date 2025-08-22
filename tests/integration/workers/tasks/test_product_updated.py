import uuid

import pytest
from rq import Queue

from robotoff.models import (
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    Prediction,
    ProductInsight,
)
from robotoff.off import generate_image_path
from robotoff.types import ProductIdentifier, ServerType
from robotoff.workers.tasks.import_image import run_import_image_job
from robotoff.workers.tasks.product_updated import (
    deleted_image_job,
    product_type_switched_job,
    update_insights_job,
)

from ...models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    LogoAnnotationFactory,
    PredictionFactory,
    ProductInsightFactory,
    clean_db,
)

DEFAULT_SERVER_TYPE = ServerType.off


@pytest.fixture()
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        # clean db
        clean_db()
    # Run the test case.
    yield
    # Tear down.
    with peewee_db:
        clean_db()


DEFAULT_BARCODE = "1234567890123"


class TestProductTypeSwitchedJob:
    def test_product_type_switched_job_product_not_found(self, mocker, caplog):
        mocker.patch(
            "robotoff.workers.tasks.product_updated.get_product_type", return_value=None
        )
        caplog.set_level("INFO", logger="robotoff.workers.tasks.product_updated")
        product_type_switched_job(
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.off)
        )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.message == (
            f"Product <Product {DEFAULT_BARCODE} | off> was not found on any server (off, obf, opf, opff). "
            "Skipping product type switch"
        )

    def test_product_type_switched_job_product_type_did_not_change(
        self, mocker, caplog
    ):
        mocker.patch(
            "robotoff.workers.tasks.product_updated.get_product_type",
            return_value="food",
        )
        caplog.set_level("INFO", logger="robotoff.workers.tasks.product_updated")
        product_type_switched_job(
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.off)
        )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.message == (
            f"Product type for <Product {DEFAULT_BARCODE} | off> has not changed, skipping product type switch"
        )

    def test_product_type_switched_job_product_not_found_second_call(
        self, mocker, caplog
    ):
        mocker.patch(
            "robotoff.workers.tasks.product_updated.get_product_type",
            return_value="beauty",
        )
        get_product_mock = mocker.patch(
            "robotoff.workers.tasks.product_updated.get_product", return_value=None
        )
        caplog.set_level("INFO", logger="robotoff.workers.tasks.product_updated")
        product_type_switched_job(
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.off)
        )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.message == (
            f"Product <Product {DEFAULT_BARCODE} | off> does not exist, skipping product type switch"
        )
        assert get_product_mock.call_count == 1
        assert get_product_mock.call_args.args == (
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.obf),
        )

    def test_product_type_switched_job_check_deleted_records_in_db(
        self, mocker, caplog, _set_up_and_tear_down, peewee_db
    ):
        other_barcode = "9876543210987"
        mocker.patch(
            "robotoff.workers.tasks.product_updated.get_product_type",
            return_value="beauty",
        )
        delete_ann_logos_mock = mocker.patch(
            "robotoff.workers.tasks.product_updated.delete_ann_logos",
            return_value=1,
        )
        enqueue_job_mock = mocker.patch(
            "robotoff.workers.tasks.product_updated.enqueue_job",
            return_value=None,
        )
        get_product_mock = mocker.patch(
            "robotoff.workers.tasks.product_updated.get_product",
            return_value={"images": {"1": {}}},
        )
        caplog.set_level("INFO", logger="robotoff.workers.tasks.product_updated")

        with peewee_db:
            image_1 = ImageModelFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                image_id="1",
                id=1000,
            )
            image_2 = ImageModelFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                image_id="2",
                id=1001,
            )
            other_image = ImageModelFactory.create(
                barcode=other_barcode, server_type=ServerType.off, image_id="1", id=1002
            )
            image_prediction_1 = ImagePredictionFactory.create(
                image=image_1, server_type=ServerType.off, id=2000
            )
            image_prediction_2 = ImagePredictionFactory.create(
                image=image_2, server_type=ServerType.off, id=2001
            )
            image_prediction_other = ImagePredictionFactory.create(
                image=other_image, server_type=ServerType.off, id=2002
            )

            LogoAnnotationFactory.create(image_prediction=image_prediction_1, id=3000)
            LogoAnnotationFactory.create(image_prediction=image_prediction_2, id=3001)
            LogoAnnotationFactory.create(
                image_prediction=image_prediction_other, id=3002
            )

            PredictionFactory.create(
                barcode=DEFAULT_BARCODE, server_type=ServerType.off, id=4000
            )
            # Create a second prediction for the same barcode but with a different type
            PredictionFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                type="nutrition_image",
                id=4001,
            )
            PredictionFactory.create(
                barcode=other_barcode, server_type=ServerType.off, id=4002
            )

            ProductInsightFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            )
            ProductInsightFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                annotation=1,
                id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            )
            ProductInsightFactory.create(
                barcode=other_barcode,
                server_type=ServerType.off,
                id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            )

        product_type_switched_job(
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.off)
        )

        with peewee_db:
            # Check that the image related to the product was deleted, and
            # that other images were not deleted
            assert sorted(
                id_ for (id_,) in ImageModel.select(ImageModel.id).tuples()
            ) == [1002]

            # Check that the image predictions related to the product were deleted
            # and that other image predictions were not deleted
            assert sorted(
                id_ for (id_,) in ImagePrediction.select(ImagePrediction.id).tuples()
            ) == [2002]

            # Check that the logo annotations related to the product were deleted
            # and that other logo annotations were not deleted
            assert sorted(
                id_ for (id_,) in LogoAnnotation.select(LogoAnnotation.id).tuples()
            ) == [3002]

            # Check that the predictions related to the product were deleted, and
            # that other predictions were not deleted
            assert sorted(
                id_ for (id_,) in Prediction.select(Prediction.id).tuples()
            ) == [4002]

            # Check that the non-annotated insights related to the product were deleted,
            # and that the annotated insights were not deleted
            assert sorted(
                id_ for (id_,) in ProductInsight.select(ProductInsight.id).tuples()
            ) == [
                uuid.UUID("00000000-0000-0000-0000-000000000002"),
                uuid.UUID("00000000-0000-0000-0000-000000000003"),
            ]

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.message == (
            f"Product type switched for <Product {DEFAULT_BARCODE} | off>, "
            "deleted 2 images, "
            "2 logos, "
            "1 logos on Elasticsearch, "
            "2 image predictions, "
            "2 predictions "
            "and 1 insights"
        )
        assert get_product_mock.call_count == 1
        assert get_product_mock.call_args.args == (
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.obf),
        )

        assert delete_ann_logos_mock.call_count == 1
        assert len(delete_ann_logos_mock.call_args.args) == 2
        assert delete_ann_logos_mock.call_args.args[1] == [3000, 3001]

        new_product_id = ProductIdentifier(
            barcode=DEFAULT_BARCODE, server_type=ServerType.obf
        )
        assert enqueue_job_mock.call_count == 2
        enqueue_job_first_call = enqueue_job_mock.call_args_list[0]
        enqueue_job_second_call = enqueue_job_mock.call_args_list[1]

        assert enqueue_job_first_call.kwargs["func"] is run_import_image_job
        assert (
            enqueue_job_first_call.kwargs["image_url"]
            == "https://images.openbeautyfacts.net/images/products/123/456/789/0123/1.jpg"
        )
        assert (
            enqueue_job_first_call.kwargs["ocr_url"]
            == "https://images.openbeautyfacts.net/images/products/123/456/789/0123/1.json"
        )
        assert enqueue_job_first_call.kwargs["product_id"] == new_product_id
        assert isinstance(enqueue_job_first_call.kwargs["queue"], Queue)

        assert enqueue_job_second_call.kwargs["diffs"] == {}
        assert enqueue_job_second_call.kwargs["force_category_prediction"] is True
        assert enqueue_job_second_call.kwargs["func"] == update_insights_job
        assert enqueue_job_second_call.kwargs["product_id"] == new_product_id
        assert isinstance(enqueue_job_second_call.kwargs["queue"], Queue)


class TestDeletedImageJob:
    def test_deleted_image_job_deleted_records_in_db(
        self, mocker, caplog, _set_up_and_tear_down, peewee_db
    ):
        product_id = ProductIdentifier(
            barcode=DEFAULT_BARCODE, server_type=ServerType.off
        )
        # ID of the image that was deleted
        deleted_image_id = "1"
        deleted_image_source_image = generate_image_path(product_id, deleted_image_id)
        other_image_id = "2"
        other_image_source_image = generate_image_path(product_id, other_image_id)
        other_barcode = "9876543210987"
        other_barcode_source_image = generate_image_path(
            ProductIdentifier(barcode=other_barcode, server_type=ServerType.off),
            other_image_id,
        )
        other_flavor_source_image = generate_image_path(
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.obf),
            deleted_image_id,
        )
        delete_ann_logos_mock = mocker.patch(
            "robotoff.workers.tasks.product_updated.delete_ann_logos",
            return_value=3,
        )
        caplog.set_level("INFO", logger="robotoff.workers.tasks.product_updated")

        with peewee_db:
            image_1 = ImageModelFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                image_id=deleted_image_id,
                id=1000,
            )
            other_image = ImageModelFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                image_id=other_image_id,
                id=1001,
            )
            image_other_barcode = ImageModelFactory.create(
                barcode=other_barcode,
                server_type=ServerType.off,
                image_id="1",
                id=1002,
            )
            image_other_flavor = ImageModelFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.obf,
                # Same image ID as the deleted image, but different server type
                image_id=deleted_image_id,
                id=1003,
            )
            image_prediction_1 = ImagePredictionFactory.create(
                image=image_1, server_type=ServerType.off, id=2000
            )
            image_prediction_other = ImagePredictionFactory.create(
                image=other_image, server_type=ServerType.off, id=2001
            )
            image_prediction_other_barcode = ImagePredictionFactory.create(
                image=image_other_barcode, server_type=ServerType.off, id=2002
            )
            image_prediction_other_flavor = ImagePredictionFactory.create(
                image=image_other_flavor, server_type=ServerType.obf, id=2003
            )
            LogoAnnotationFactory.create(
                image_prediction=image_prediction_1, id=3000, index=0
            )
            LogoAnnotationFactory.create(
                image_prediction=image_prediction_1, id=3001, index=1
            )
            LogoAnnotationFactory.create(
                image_prediction=image_prediction_1, id=3002, index=2
            )
            LogoAnnotationFactory.create(
                image_prediction=image_prediction_1, id=3003, index=3
            )
            LogoAnnotationFactory.create(
                image_prediction=image_prediction_other, id=3004
            )
            LogoAnnotationFactory.create(
                image_prediction=image_prediction_other_barcode, id=3005
            )
            LogoAnnotationFactory.create(
                image_prediction=image_prediction_other_flavor, id=3006
            )
            # Create two predictions for the deleted image
            PredictionFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                source_image=deleted_image_source_image,
                id=4000,
            )
            PredictionFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                source_image=deleted_image_source_image,
                id=4001,
            )
            # Create a second prediction for the same barcode but with a different image
            # Should not be deleted
            PredictionFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                source_image=other_image_source_image,
                id=4002,
            )
            # Create a prediction for another barcode
            # Should not be deleted
            PredictionFactory.create(
                barcode=other_barcode,
                server_type=ServerType.off,
                source_image=other_barcode_source_image,
                id=4003,
            )

            # Prediction for other flavor of the same barcode, should not
            # be deleted
            PredictionFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.obf,
                source_image=other_flavor_source_image,
                id=4004,
            )
            # Create insights related to the deleted image
            # One without annotation and one with annotation
            # The one without annotation should be deleted
            # The one with annotation should not be deleted
            ProductInsightFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                source_image=deleted_image_source_image,
                id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            )
            ProductInsightFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                annotation=1,
                source_image=deleted_image_source_image,
                id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            )
            ProductInsightFactory.create(
                barcode=other_barcode,
                server_type=ServerType.off,
                source_image=other_image_source_image,
                id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            )

            deleted_image_job(
                ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.off),
                image_id=deleted_image_id,
            )

        with peewee_db:
            # Check that all images are still in DB (including the deleted one)
            assert sorted(
                id_ for (id_,) in ImageModel.select(ImageModel.id).tuples()
            ) == [
                1000,
                1001,
                1002,
                1003,
            ]
            # Check that the deleted image is marked as deleted
            assert ImageModel.get_by_id(1000).deleted is True

            assert sorted(
                id_ for (id_,) in ImagePrediction.select(ImagePrediction.id).tuples()
            ) == [2001, 2002, 2003]

            assert sorted(
                id_ for (id_,) in LogoAnnotation.select(LogoAnnotation.id).tuples()
            ) == [3004, 3005, 3006]

            assert sorted(
                id_ for (id_,) in Prediction.select(Prediction.id).tuples()
            ) == [
                4002,
                4003,
                4004,
            ]

            assert sorted(
                id_ for (id_,) in ProductInsight.select(ProductInsight.id).tuples()
            ) == [
                uuid.UUID("00000000-0000-0000-0000-000000000002"),
                uuid.UUID("00000000-0000-0000-0000-000000000003"),
            ]

        assert len(caplog.records) == 1
        record = caplog.records[0]

        assert record.message == (
            f"Image deleted (product: <Product {DEFAULT_BARCODE} | off>, image ID: {deleted_image_id}), "
            "4 logo(s), "
            "3 logo(s) on Elasticsearch, "
            "1 image prediction(s), "
            "2 prediction(s) and "
            "1 insight(s)"
        )

        assert delete_ann_logos_mock.call_count == 1
        assert len(delete_ann_logos_mock.call_args.args) == 2
        assert delete_ann_logos_mock.call_args.args[1] == [3000, 3001, 3002, 3003]
