import pytest
from rq import Queue

from robotoff.models import (
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    Prediction,
    ProductInsight,
)
from robotoff.types import ProductIdentifier, ServerType
from robotoff.workers.tasks.import_image import run_import_image_job
from robotoff.workers.tasks.product_updated import (
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
                barcode=DEFAULT_BARCODE, server_type=ServerType.off, image_id="1"
            )
            other_image = ImageModelFactory.create(
                barcode=other_barcode, server_type=ServerType.off, image_id="2"
            )
            image_prediction_1 = ImagePredictionFactory.create(
                image=image_1, server_type=ServerType.off, prediction_id="1"
            )
            image_prediction_other = ImagePredictionFactory.create(
                image=other_image, server_type=ServerType.off, prediction_id="2"
            )
            LogoAnnotationFactory.create(image_prediction=image_prediction_1, id=52)
            LogoAnnotationFactory.create(image_prediction=image_prediction_other)
            PredictionFactory.create(
                barcode=DEFAULT_BARCODE, server_type=ServerType.off
            )
            # Create a second prediction for the same barcode but with a different type
            PredictionFactory.create(
                barcode=DEFAULT_BARCODE,
                server_type=ServerType.off,
                type="nutrition_image",
            )
            PredictionFactory.create(barcode=other_barcode, server_type=ServerType.off)
            ProductInsightFactory.create(
                barcode=DEFAULT_BARCODE, server_type=ServerType.off
            )
            ProductInsightFactory.create(
                barcode=DEFAULT_BARCODE, server_type=ServerType.off, annotation=1
            )
            ProductInsightFactory.create(
                barcode=other_barcode, server_type=ServerType.off
            )

        product_type_switched_job(
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.off)
        )

        with peewee_db:
            # Check that the image related to the product was deleted
            assert (
                not ImageModel.select()
                .where(
                    ImageModel.barcode == DEFAULT_BARCODE,
                    ImageModel.server_type == ServerType.off,
                )
                .exists()
            )
            # Check that other images were not deleted
            assert (
                ImageModel.select()
                .where(
                    ImageModel.barcode == other_barcode,
                    ImageModel.server_type == ServerType.off,
                )
                .exists()
            )
            # Check that the image predictions related to the product were deleted
            assert (
                not ImagePrediction.select()
                .where(ImagePrediction.image == image_prediction_1.image)
                .exists()
            )
            # Check that other image predictions were not deleted
            assert (
                ImagePrediction.select()
                .where(ImagePrediction.image == image_prediction_other.image)
                .exists()
            )
            # Check that the logo annotations related to the product were deleted
            assert (
                not LogoAnnotation.select()
                .where(
                    LogoAnnotation.image_prediction == image_prediction_1,
                )
                .exists()
            )
            # Check that other logo annotations were not deleted
            assert (
                LogoAnnotation.select()
                .where(
                    LogoAnnotation.image_prediction == image_prediction_other,
                )
                .exists()
            )
            # Check that the predictions related to the product were deleted
            assert (
                not Prediction.select()
                .where(
                    Prediction.barcode == DEFAULT_BARCODE,
                    Prediction.server_type == ServerType.off,
                )
                .exists()
            )
            # Check that other predictions were not deleted
            assert (
                Prediction.select()
                .where(
                    Prediction.barcode == other_barcode,
                    Prediction.server_type == ServerType.off,
                )
                .exists()
            )
            # Check that the non-annotated insights related to the product were deleted
            assert (
                len(
                    list(
                        ProductInsight.select().where(
                            ProductInsight.barcode == DEFAULT_BARCODE,
                            ProductInsight.server_type == ServerType.off,
                        )
                    )
                )
                == 1
            )
            # Check that other insights were not deleted
            assert (
                ProductInsight.select()
                .where(
                    ProductInsight.barcode == other_barcode,
                    ProductInsight.server_type == ServerType.off,
                )
                .exists()
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.message == (
            f"Product type switched for <Product {DEFAULT_BARCODE} | off>, "
            "deleted 1 images, "
            "1 logos, "
            "1 logos on Elasticsearch, "
            "1 image predictions, "
            "2 predictions "
            "and 1 insights"
        )
        assert get_product_mock.call_count == 1
        assert get_product_mock.call_args.args == (
            ProductIdentifier(barcode=DEFAULT_BARCODE, server_type=ServerType.obf),
        )

        assert delete_ann_logos_mock.call_count == 1
        assert len(delete_ann_logos_mock.call_args.args) == 2
        assert delete_ann_logos_mock.call_args.args[1] == [52]

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
