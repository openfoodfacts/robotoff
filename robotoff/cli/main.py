import pathlib
import sys
from pathlib import Path
from typing import Optional

import typer

from robotoff.types import ObjectDetectionModel, PredictionType, WorkerQueue

app = typer.Typer()


@app.command()
def run_scheduler():
    """Launch the scheduler service."""
    from robotoff import scheduler
    from robotoff.utils import get_logger

    # Defining a root logger
    get_logger()
    scheduler.run()


@app.command()
def run_worker(
    queues: list[WorkerQueue] = typer.Argument(
        ..., help="Names of the queues to listen to"
    ),
    burst: bool = typer.Option(
        False, help="Run in burst mode (quit after all work is done)"
    ),
):
    """Launch a worker."""
    from robotoff.workers.main import run

    run(queues=[x.value for x in queues], burst=burst)


@app.command()
def regenerate_ocr_insights(
    barcode: str = typer.Argument(..., help="Barcode of the product")
) -> None:
    """Regenerate OCR predictions/insights for a specific product and import
    them."""
    from robotoff import settings
    from robotoff.insights import importer
    from robotoff.insights.extraction import (
        DEFAULT_OCR_PREDICTION_TYPES,
        extract_ocr_predictions,
    )
    from robotoff.models import db
    from robotoff.off import generate_json_ocr_url
    from robotoff.products import get_product
    from robotoff.utils import get_logger

    logger = get_logger()

    product = get_product(barcode, ["images"])
    if product is None:
        raise ValueError(f"product not found: {barcode}")

    predictions = []
    for image_id in product["images"]:
        if not image_id.isdigit():
            continue

        ocr_url = generate_json_ocr_url(barcode, image_id)
        predictions += extract_ocr_predictions(
            barcode, ocr_url, DEFAULT_OCR_PREDICTION_TYPES
        )

    with db:
        imported = importer.import_insights(predictions, settings.OFF_SERVER_DOMAIN)

    logger.info("Import finished, %s insights imported", imported)


@app.command()
def generate_ocr_predictions(
    input_path: Path = typer.Argument(
        ..., help="Path to a (gzipped-)OCR JSONL archive"
    ),
    prediction_type: PredictionType = typer.Argument(
        ..., help="Type of the predictions to generate (label, brand,...)"
    ),
    output: Optional[Path] = typer.Option(
        None,
        help="File to write output to, stdout if not specified. Gzipped output are supported.",
        dir_okay=False,
        writable=True,
    ),
) -> None:
    """Generate OCR predictions of the requested type."""
    from robotoff.cli import insights
    from robotoff.utils import get_logger

    get_logger()
    insights.run_from_ocr_archive(input_path, prediction_type, output)


@app.command()
def predict_category(output: str) -> None:
    """Predict categories from the product JSONL dataset stored in `datasets`
    directory."""
    from robotoff import settings
    from robotoff.prediction.category.matcher import predict_from_dataset
    from robotoff.products import ProductDataset
    from robotoff.utils import dump_jsonl

    dataset = ProductDataset(settings.JSONL_DATASET_PATH)
    insights = predict_from_dataset(dataset)
    dict_insights = (i.to_dict() for i in insights)
    dump_jsonl(output, dict_insights)


@app.command()
def download_dataset(minify: bool = False) -> None:
    """Download Open Food Facts dataset and save it in `datasets` directory."""
    from robotoff.products import fetch_dataset, has_dataset_changed
    from robotoff.utils import get_logger

    get_logger()

    if has_dataset_changed():
        fetch_dataset(minify)


@app.command()
def categorize(
    barcode: str,
    deepest_only: bool = False,
) -> None:
    """Predict product categories based on the neural category classifier.

    deepest_only: controls whether the returned predictions should only contain the deepmost
    categories for a predicted taxonomy chain.
    For example, if we predict 'fresh vegetables' -> 'legumes' -> 'beans' for a product,
    setting deepest_only=True will return 'beans'."""
    from robotoff.prediction.category.neural.category_classifier import (
        CategoryClassifier,
    )
    from robotoff.products import get_product
    from robotoff.taxonomy import TaxonomyType, get_taxonomy

    product = get_product(barcode)
    if product is None:
        print(f"Product {barcode} not found")
        return

    predictions = CategoryClassifier(get_taxonomy(TaxonomyType.category.name)).predict(
        product, deepest_only
    )

    if predictions:
        for prediction in predictions:
            print(f"{prediction.value_tag}: {prediction.data['confidence']}")
    else:
        print(f"Nothing predicted for product {barcode}")


@app.command()
def import_insights(
    prediction_type: Optional[PredictionType] = typer.Option(
        None,
        help="Type of the prediction to generate, only needed when --generate-from is used",
    ),
    batch_size: int = typer.Option(
        128,
        help="Number of insights that are imported in each atomic SQL transaction",
    ),
    input_path: Optional[pathlib.Path] = typer.Option(
        None,
        help="Input path of the JSONL archive, is incompatible with --generate-from",
    ),
    generate_from: Optional[pathlib.Path] = typer.Option(
        None, help="Input path of the OCR archive, is incompatible with --input-path"
    ),
) -> None:
    """Import insights from a prediction JSONL archive (with --input-path
    option), or generate them on the fly from an OCR archive (with
    --generate-from option)."""
    import tqdm
    from more_itertools import chunked

    from robotoff import settings
    from robotoff.cli.insights import generate_from_ocr_archive, insights_iter
    from robotoff.insights import importer
    from robotoff.models import db
    from robotoff.utils import get_logger

    logger = get_logger()

    if generate_from is not None:
        logger.info(f"Generating and importing insights from {generate_from}")
        if prediction_type is None:
            sys.exit("Required option: --prediction-type")

        predictions = generate_from_ocr_archive(generate_from, prediction_type)
    elif input_path is not None:
        logger.info(f"Importing insights from {input_path}")
        predictions = insights_iter(input_path)
    else:
        raise ValueError("--generate-from or --input-path must be provided")

    imported = 0
    with db.connection_context():
        for prediction_batch in tqdm.tqdm(
            chunked(predictions, batch_size), desc="prediction batch"
        ):
            # Create a new transaction for every batch
            with db.atomic():
                batch_imported = importer.import_insights(
                    prediction_batch,
                    settings.OFF_SERVER_DOMAIN,
                )
                logger.info(f"{batch_imported} insights imported in batch")
                imported += batch_imported

    logger.info(f"{imported} insights imported")


@app.command()
def refresh_insights(
    barcode: Optional[str] = typer.Option(
        None,
        help="Refresh a specific product. If not provided, all products are updated",
    ),
    batch_size: int = typer.Option(
        100, help="Number of products to send in a worker tasks"
    ),
):
    """Refresh insights based on available predictions.

    If a `barcode` is provided, only the insights of this product is
    refreshed, otherwise insights of all products are refreshed.
    """
    import tqdm
    from more_itertools import chunked
    from peewee import fn

    from robotoff import settings
    from robotoff.insights.importer import refresh_insights as refresh_insights_
    from robotoff.models import Prediction as PredictionModel
    from robotoff.models import db
    from robotoff.utils import get_logger
    from robotoff.workers.queues import enqueue_job, low_queue
    from robotoff.workers.tasks import refresh_insights_job

    logger = get_logger()

    if barcode is not None:
        logger.info(f"Refreshing product {barcode}")
        imported = refresh_insights_(barcode, settings.OFF_SERVER_DOMAIN)
        logger.info(f"Refreshed insights: {imported}")
    else:
        logger.info("Launching insight refresh on full database")
        with db:
            barcodes = [
                barcode
                for (barcode,) in PredictionModel.select(
                    fn.Distinct(PredictionModel.barcode)
                ).tuples()
            ]

        batches = list(chunked(barcodes, batch_size))
        confirm = typer.confirm(
            f"{len(batches)} jobs are going to be launched, confirm?"
        )

        if not confirm:
            return

        logger.info("Adding refresh_insights jobs in queue...")
        for barcode_batch in tqdm.tqdm(batches, desc="barcode batch"):
            enqueue_job(
                refresh_insights_job,
                low_queue,
                job_kwargs={"result_ttl": 0, "timeout": "5m"},
                barcodes=barcode_batch,
                server_domain=settings.OFF_SERVER_DOMAIN,
            )


@app.command()
def import_images_in_db(
    batch_size: int = typer.Option(
        500, help="Number of items to send in a worker tasks"
    ),
):
    """Make sure that every image available in MongoDB is saved in `image`
    table."""
    import tqdm
    from more_itertools import chunked

    from robotoff import settings
    from robotoff.models import ImageModel, db
    from robotoff.off import generate_image_path
    from robotoff.products import get_product_store
    from robotoff.utils import get_logger
    from robotoff.workers.queues import enqueue_job, low_queue
    from robotoff.workers.tasks.import_image import save_image_job

    logger = get_logger()

    with db:
        logger.info("Fetching existing images in DB...")
        existing_images = set(
            ImageModel.select(ImageModel.barcode, ImageModel.image_id).tuples()
        )

    store = get_product_store()
    to_add = []
    for product in tqdm.tqdm(
        store.iter_product(projection=["images", "code"]), desc="product"
    ):
        barcode = product.barcode
        for image_id in (id_ for id_ in product.images.keys() if id_.isdigit()):
            if (barcode, image_id) not in existing_images:
                to_add.append((barcode, generate_image_path(barcode, image_id)))

    batches = list(chunked(to_add, batch_size))
    if typer.confirm(
        f"{len(batches)} add image jobs are going to be launched, confirm?"
    ):
        for batch in tqdm.tqdm(batches, desc="job"):
            enqueue_job(
                save_image_job,
                low_queue,
                job_kwargs={"result_ttl": 0},
                batch=batch,
                server_domain=settings.OFF_SERVER_DOMAIN,
            )


@app.command()
def run_object_detection_model(
    model_name: ObjectDetectionModel = typer.Argument(
        ..., help="Name of the object detection model"
    ),
    limit: Optional[int] = typer.Option(None, help="Maximum numbers of job to launch"),
):
    """Launch object detection model jobs on all missing images (images
    without an ImagePrediction item for this model) in DB."""
    from typing import Callable

    import tqdm
    from peewee import JOIN

    from robotoff import settings
    from robotoff.models import ImageModel, ImagePrediction, db
    from robotoff.off import generate_image_url
    from robotoff.workers.queues import enqueue_job, low_queue
    from robotoff.workers.tasks.import_image import (
        run_logo_object_detection,
        run_nutriscore_object_detection,
        run_nutrition_table_object_detection,
    )

    kwargs = {}
    if model_name == ObjectDetectionModel.universal_logo_detector:
        func: Callable = run_logo_object_detection
        kwargs["process_logos"] = False
    elif model_name == ObjectDetectionModel.nutrition_table:
        func = run_nutrition_table_object_detection
    else:
        func = run_nutriscore_object_detection

    with db:
        query = (
            ImageModel.select(ImageModel.barcode, ImageModel.id)
            .join(
                ImagePrediction,
                JOIN.LEFT_OUTER,
                on=(
                    (ImagePrediction.image_id == ImageModel.id)
                    & (ImagePrediction.model_name == model_name)
                ),
            )
            .where(ImagePrediction.model_name.is_null())
            .tuples()
        )
        if limit:
            query = query.limit(limit)
        missing_items = list(query)

    if limit:
        missing_items = missing_items[:limit]

    if typer.confirm(f"{len(missing_items)} jobs are going to be launched, confirm?"):
        for barcode, image_id in tqdm.tqdm(missing_items, desc="image"):
            image_url = generate_image_url(barcode, image_id)
            enqueue_job(
                func,
                low_queue,
                job_kwargs={"result_ttl": 0},
                barcode=barcode,
                image_url=image_url,
                server_domain=settings.OFF_SERVER_DOMAIN,
                **kwargs,
            )


@app.command()
def init_elasticsearch(
    load_index: bool = False,
    load_data: bool = True,
    to_load: Optional[list[str]] = None,
) -> None:
    """
    This command is used for manual insertion of the Elasticsearch data and/or indexes
    for products and categorties.

    to_load specifies which indexes/data should be loaded - supported values are
    in robotoff.settings.ElasticsearchIndex.
    """
    from robotoff.elasticsearch.export import ElasticsearchExporter
    from robotoff.settings import ElasticsearchIndex
    from robotoff.utils import get_logger
    from robotoff.utils.es import get_es_client

    logger = get_logger()

    es_exporter = ElasticsearchExporter(get_es_client())

    if not to_load:
        return

    for item in to_load:
        if item not in ElasticsearchIndex.SUPPORTED_INDICES:
            logger.error(f"Skipping over unknown Elasticsearch type: '{item}'")
            continue
        if load_index:
            es_exporter.load_index(item, ElasticsearchIndex.SUPPORTED_INDICES[item])
        if load_data:
            es_exporter.export_index_data(item)


@app.command()
def add_logo_to_ann(sleep_time: float = 0.5) -> None:
    import time
    from itertools import groupby

    import requests
    import tqdm

    from robotoff.logos import add_logos_to_ann, get_stored_logo_ids
    from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
    from robotoff.utils import get_logger

    logger = get_logger()
    seen = get_stored_logo_ids()

    with db:
        logos_iter = tqdm.tqdm(
            LogoAnnotation.select()
            .join(ImagePrediction)
            .join(ImageModel)
            .where(LogoAnnotation.nearest_neighbors.is_null())
            .order_by(ImageModel.id)
            .iterator()
        )
        for _, logo_batch in groupby(logos_iter, lambda x: x.image_prediction.image.id):
            logos = list(logo_batch)

            if all(logo.id in seen for logo in logos):
                continue

            image = logos[0].image_prediction.image
            logger.info(f"Adding logos of image {image.id}")
            try:
                added = add_logos_to_ann(image, logos)
            except requests.exceptions.ReadTimeout:
                logger.warning("Request timed-out during logo addition")
                continue

            logger.info(f"Added: {added}")

            if sleep_time:
                time.sleep(sleep_time)


@app.command()
def import_logos(
    data_path: pathlib.Path,
    model_name: str = "universal-logo-detector",
    model_version: str = "tf-universal-logo-detector-1.0",
) -> None:
    from robotoff.cli.logos import insert_batch
    from robotoff.models import db
    from robotoff.utils import get_logger

    logger = get_logger()
    logger.info("Starting image prediction import...")

    with db:
        inserted = insert_batch(data_path, model_name, model_version)

    logger.info("{} image predictions inserted".format(inserted))


@app.command()
def export_logo_annotation(
    output: pathlib.Path,
    server_domain: Optional[str] = None,
    annotated: Optional[bool] = None,
) -> None:
    from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
    from robotoff.utils import dump_jsonl

    with db:
        where_clauses = []

        if server_domain is not None:
            where_clauses.append(ImageModel.server_domain == server_domain)

        if annotated is not None:
            where_clauses.append(LogoAnnotation.annotation_value.is_null(not annotated))

        query = LogoAnnotation.select().join(ImagePrediction).join(ImageModel)
        if where_clauses:
            query = query.where(*where_clauses)

        logo_iter = query.iterator()
        dict_iter = (logo.to_dict() for logo in logo_iter)
        dump_jsonl(output, dict_iter)


@app.command()
def export_logos_ann(
    output: pathlib.Path = typer.Argument(
        ...,
        help="Path to the output file, can either have .json or .json.gz as "
        "extension",
    ),
) -> None:
    """Export all information about logo in DB necessary to generate logo
    crops."""
    from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
    from robotoff.utils import dump_jsonl

    with db:
        query = (
            LogoAnnotation.select(
                LogoAnnotation.id,
                LogoAnnotation.bounding_box,
                LogoAnnotation.score,
                ImageModel.image_id,
                ImageModel.barcode,
            )
            .join(ImagePrediction)
            .join(ImageModel)
        )
        dump_jsonl(output, query.dicts().iterator())


def main() -> None:
    app()
