import datetime
from pathlib import Path
from typing import Optional

import typer
from openfoodfacts.types import Environment, Flavor

from robotoff.products import fetch_parquet_datasets
from robotoff.types import (
    ImportImageFlag,
    ObjectDetectionModel,
    PredictionType,
    ProductIdentifier,
    ServerType,
)

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
def download_taxonomies(
    download_newer: bool = typer.Option(
        False,
        help="If True, we check if a new version of the taxonomies is available and "
        "download it if so. If False, we only download the taxonomies if they are not "
        "already cached locally.",
    )
):
    """Download all taxonomies."""
    from robotoff.taxonomy import download_taxonomies as _download_taxonomies
    from robotoff.utils import get_logger

    logger = get_logger()
    _download_taxonomies(download_newer=download_newer)
    logger.info("All taxonomies downloaded successfully.")


@app.command()
def run_worker(
    queues: list[str] = typer.Argument(..., help="Names of the queues to listen to"),
    burst: bool = typer.Option(
        False, help="Run in burst mode (quit after all work is done)"
    ),
):
    """Launch a worker."""
    from robotoff.workers.main import run

    run(queues=queues, burst=burst)


@app.command()
def run_update_listener():
    """Launch a process that listens to product updates published on Redis
    stream."""
    from robotoff import settings
    from robotoff.utils.logger import get_logger
    from robotoff.workers.update_listener import run_update_listener

    get_logger()
    settings.init_sentry()
    run_update_listener()


@app.command()
def process_updates_since(
    since: datetime.datetime = typer.Argument(
        ..., help="Datetime to start processing updates from"
    )
):
    """Process all updates since a given datetime."""
    from robotoff import settings
    from robotoff.utils.logger import get_logger
    from robotoff.workers.update_listener import UpdateListener, get_redis_client

    logger = get_logger()
    logger.info("Processing Redis updates since %s", since)
    redis_client = get_redis_client()
    update_listener = UpdateListener(
        redis_client=redis_client,
        redis_latest_id_key=settings.REDIS_LATEST_ID_KEY,
    )
    update_listener.process_updates_since(since)


@app.command()
def create_redis_update(
    barcode: str = typer.Option(default="3274080005003", help="barcode of the product"),
    flavor: str = typer.Option(default="off", help="flavor of the product"),
    user_id: str = typer.Option(default="app-user", help="user id"),
    action: str = typer.Option(default="updated", help="user action"),
    comment: Optional[str] = typer.Option(
        default="modification: ", help="user comment"
    ),
    uploaded_image_id: Optional[int] = typer.Option(
        default=None, help="ID of the uploaded image"
    ),
):
    """Create a new product update event in Redis.

    This command is meant for **local development only**.
    """
    import json

    from openfoodfacts.types import JSONType

    from robotoff import settings
    from robotoff.utils.logger import get_logger
    from robotoff.workers.update_listener import get_redis_client

    get_logger()
    client = get_redis_client()
    flavor_to_product_type = {
        "off": "food",
        "obf": "beauty",
        "opff": "petfood",
        "opf": "product",
    }
    event = {
        "code": barcode,
        "flavor": flavor,
        "user_id": user_id,
        "action": action,
        "comment": comment,
        "product_type": flavor_to_product_type[flavor],
    }

    diffs: JSONType
    if uploaded_image_id is not None:
        diffs = {"uploaded_images": {"add": [uploaded_image_id]}}
    else:
        diffs = {"fields": {"change": ["generic_name", "generic_name_fr"]}}

    event["diffs"] = json.dumps(diffs)
    client.xadd(settings.PRODUCT_UDPATE_STREAM_NAME, event)
    typer.echo(
        f"Event added to Redis stream {settings.PRODUCT_UDPATE_STREAM_NAME}: {event}"
    )


@app.command()
def create_redis_ocr_ready_event(
    barcode: str = typer.Option(
        default="3274080005003",
        help="barcode of the product associated with the OCR result",
    ),
    product_type: str = typer.Option(
        default="food",
        help="product type of the product associated with the OCR result",
    ),
    image_id: str = typer.Option(
        default="1", help="image ID associated with the OCR result"
    ),
):
    """Create a new `ocr_ready` event in Redis.
    This event is published when a new OCR result (response from Google Cloud Vision
    saved as a JSON file) is available for a product image.

    This command is meant for **local development only**.
    """
    from robotoff import settings
    from robotoff.off import generate_json_ocr_url
    from robotoff.utils.logger import get_logger
    from robotoff.workers.update_listener import get_redis_client

    get_logger()
    client = get_redis_client()
    json_url = generate_json_ocr_url(
        ProductIdentifier(barcode, ServerType.from_product_type(product_type)), image_id
    )
    event = {
        "code": barcode,
        "product_type": product_type,
        "image_id": image_id,
        "json_url": json_url,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).timestamp(),
    }

    client.xadd(settings.OCR_READY_STREAM_NAME, event)
    typer.echo(
        f"Event added to Redis stream '{settings.OCR_READY_STREAM_NAME}': {event}"
    )


@app.command()
def regenerate_ocr_insights(
    barcode: str = typer.Argument(..., help="Barcode of the product"),
    server_type: ServerType = typer.Option(
        ServerType.off, help="Server type of the product"
    ),
    ocr_prediction_types: Optional[list[PredictionType]] = typer.Option(
        None, help="Types of OCR prediction to use"
    ),
) -> None:
    """Regenerate OCR predictions/insights for a specific product and import
    them."""
    from robotoff.insights import importer
    from robotoff.insights.extraction import (
        DEFAULT_OCR_PREDICTION_TYPES,
        extract_ocr_predictions,
    )
    from robotoff.models import db
    from robotoff.off import generate_json_ocr_url
    from robotoff.products import get_product
    from robotoff.utils import get_logger

    if ocr_prediction_types is None:
        ocr_prediction_types = DEFAULT_OCR_PREDICTION_TYPES

    logger = get_logger()

    product_id = ProductIdentifier(barcode, server_type)
    product = get_product(product_id, ["images"])
    if product is None:
        raise ValueError(f"product not found: {barcode}")

    predictions = []
    for image_id in product["images"]:
        if not image_id.isdigit():
            continue

        ocr_url = generate_json_ocr_url(product_id, image_id)
        predictions += extract_ocr_predictions(
            product_id, ocr_url, ocr_prediction_types
        )

    with db:
        import_result = importer.import_insights(predictions, server_type)
        logger.info(import_result)


@app.command()
def generate_ocr_predictions(
    input_path: Path = typer.Argument(
        ..., help="Path to a (gzipped-)OCR JSONL archive"
    ),
    prediction_type: list[PredictionType] = typer.Option(
        None, help="Type of the predictions to generate (label, brand,...)"
    ),
    server_type: ServerType = typer.Option(
        ServerType.off, help="Server type of the archive"
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
    insights.run_from_ocr_archive(
        input_path, prediction_type or None, server_type, output
    )


@app.command()
def download_dataset(
    download_jsonl: bool = True,
    download_parquet: bool = True,
    minify_jsonl: bool = False,
) -> None:
    """Download Open Food Facts dataset and save it in `datasets` directory."""
    from robotoff.products import fetch_jsonl_dataset, has_jsonl_dataset_changed
    from robotoff.utils import get_logger

    logger = get_logger()

    if download_jsonl:
        if has_jsonl_dataset_changed():
            fetch_jsonl_dataset(minify_jsonl)
        else:
            logger.info("JSONL dataset is up to date, skipping download.")

    if download_parquet:
        logger.info("Fetching parquet datasets...")
        fetch_parquet_datasets()


@app.command()
def categorize(
    barcode: str,
    flavor: Flavor = typer.Option(Flavor.off, help="Flavor of the product"),
    environment: Environment = typer.Option(
        Environment.org,
        help="The environment to use, production (org) or staging (net)",
    ),
    deepest_only: bool = False,
    threshold: Optional[float] = typer.Option(0.5, help="detection threshold to use"),
    triton_uri: Optional[str] = typer.Option(
        None,
        help="URI of the Triton server to use. If not provided, the default value from settings is used.",
    ),
) -> None:
    """Predict product categories based on the neural category classifier.

    deepest_only: controls whether the returned predictions should only contain
    the deepmost categories for a predicted taxonomy chain. For example, if we
    predict 'fresh vegetables' -> 'legumes' -> 'beans' for a product, setting
    deepest_only=True will return 'beans'."""
    import logging
    import typing

    from openfoodfacts.api import API
    from openfoodfacts.types import APIVersion, JSONType

    from robotoff import settings
    from robotoff.prediction.category.neural.category_classifier import (
        CategoryClassifier,
    )
    from robotoff.taxonomy import TaxonomyType, get_taxonomy
    from robotoff.utils import get_logger

    get_logger(level=logging.DEBUG)

    api = API(
        user_agent=settings.ROBOTOFF_USER_AGENT,
        version=APIVersion.v3_5,
        flavor=flavor,
        environment=environment,
    )
    product = api.product.get(code=barcode)

    if product is None:
        typer.echo(f"product not found: {barcode}")
        typer.Exit(0)

    product = typing.cast(JSONType, product)
    product_id = ProductIdentifier(barcode, ServerType[flavor])

    predictions, debug = CategoryClassifier(
        get_taxonomy(TaxonomyType.category.name, offline=True)
    ).predict(
        product,
        product_id,
        deepest_only,
        threshold=threshold,
        triton_uri=triton_uri,
    )
    typer.echo(f"Debug information: {debug}")

    if predictions:
        for prediction in predictions:
            print(f"{prediction.value_tag}: {prediction.confidence}")
    else:
        print(f"Nothing predicted for {product_id}")


@app.command()
def import_insights(
    prediction_type: list[PredictionType] = typer.Option(
        None,
        help="Type of the prediction to generate, only used when --generate-from is used",
    ),
    batch_size: int = typer.Option(
        128, help="Number of insights that are imported in each atomic SQL transaction"
    ),
    input_path: Optional[Path] = typer.Option(
        None,
        help="Input path of the JSONL archive, is incompatible with --generate-from",
    ),
    generate_from: Optional[Path] = typer.Option(
        None, help="Input path of the OCR archive, is incompatible with --input-path"
    ),
    server_type: ServerType = typer.Option(
        ServerType.off, help="Server type of the product"
    ),
) -> None:
    """Import insights from a prediction JSONL archive (with --input-path
    option), or generate them on the fly from an OCR archive (with
    --generate-from option)."""
    import tqdm
    from more_itertools import chunked

    from robotoff.cli.insights import generate_from_ocr_archive, prediction_iter
    from robotoff.insights import importer
    from robotoff.models import db
    from robotoff.utils import get_logger

    logger = get_logger()

    if generate_from is not None:
        prediction_types = [] if prediction_type is None else prediction_type
        logger.info("Generating and importing insights from %s", generate_from)
        predictions = generate_from_ocr_archive(
            generate_from, prediction_types, server_type
        )
    elif input_path is not None:
        logger.info("Importing insights from %s", input_path)
        predictions = prediction_iter(input_path)
    else:
        raise ValueError("--generate-from or --input-path must be provided")

    with db.connection_context():
        for prediction_batch in tqdm.tqdm(
            chunked(predictions, batch_size), desc="prediction batch"
        ):
            # Create a new transaction for every batch
            with db.atomic():
                import_results = importer.import_insights(prediction_batch, server_type)
                logger.info(import_results)


@app.command()
def refresh_insights(
    barcode: Optional[str] = typer.Option(
        None,
        help="Refresh a specific product. If not provided, all products are updated",
    ),
    prediction_type: Optional[PredictionType] = typer.Option(
        None,
        help="Type of the prediction to refresh, if any. This option is only "
        "used when --barcode is not used.",
    ),
    server_type: ServerType = typer.Option(
        ServerType.off, help="Server type of the product"
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

    from robotoff.insights.importer import refresh_insights as refresh_insights_
    from robotoff.models import Prediction as PredictionModel
    from robotoff.models import db
    from robotoff.utils import get_logger
    from robotoff.workers.queues import enqueue_job, low_queue
    from robotoff.workers.tasks import refresh_insights_job

    logger = get_logger()

    if barcode is not None:
        product_id = ProductIdentifier(barcode, server_type)
        logger.info("Refreshing %s", product_id)
        with db:
            imported = refresh_insights_(product_id)
        logger.info("Refreshed insights: %s", imported)
    else:
        logger.info("Launching insight refresh on full database")
        with db:
            where_clauses = [PredictionModel.server_type == server_type.name]
            if prediction_type is not None:
                where_clauses.append(PredictionModel.type == prediction_type.name)
            product_ids = [
                ProductIdentifier(barcode, server_type)
                for (barcode,) in PredictionModel.select(
                    fn.Distinct(PredictionModel.barcode)
                )
                .where(*where_clauses)
                .tuples()
            ]

        batches = list(chunked(product_ids, batch_size))
        confirm = typer.confirm(
            f"{len(batches)} jobs are going to be launched, confirm?"
        )

        if not confirm:
            return

        logger.info("Adding refresh_insights jobs in queue...")
        for product_id_batch in tqdm.tqdm(batches, desc="barcode batch"):
            enqueue_job(
                refresh_insights_job,
                low_queue,
                job_kwargs={"result_ttl": 0, "timeout": "5m"},
                product_ids=product_id_batch,
            )


@app.command()
def import_images_in_db(
    server_type: ServerType = typer.Option(
        ServerType.off, help="Server type of the product"
    ),
    batch_size: int = typer.Option(
        500, help="Number of items to send in a worker tasks"
    ),
):
    """Make sure that every image available in MongoDB is saved in `image`
    table."""
    import tqdm
    from more_itertools import chunked

    from robotoff.models import ImageModel, db
    from robotoff.off import generate_image_path
    from robotoff.products import DBProductStore, get_product_store
    from robotoff.utils import get_logger
    from robotoff.workers.queues import enqueue_job, low_queue
    from robotoff.workers.tasks.import_image import save_image_job

    logger = get_logger()

    with db:
        logger.info("Fetching existing images in DB...")
        existing_images = set(
            ImageModel.select(ImageModel.barcode, ImageModel.image_id)
            .where(ImageModel.server_type == server_type.name)
            .tuples()
        )

    store: DBProductStore = get_product_store(server_type)
    to_add: list[tuple[ProductIdentifier, str]] = []
    for product in tqdm.tqdm(
        store.iter_product(projection=["images", "code"]), desc="product"
    ):
        barcode = product.barcode
        for image_id in (id_ for id_ in product.images.keys() if id_.isdigit()):
            if (barcode, image_id) not in existing_images:
                product_id = ProductIdentifier(barcode, server_type)
                to_add.append(
                    (
                        product_id,
                        generate_image_path(product_id, image_id),
                    )
                )

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
                server_type=server_type,
            )


@app.command()
def run_category_prediction(
    triton_uri: Optional[str] = typer.Option(
        None,
        help="URI of the Triton Inference Server to use. If not provided, the default value from settings is used.",
    ),
    limit: Optional[int] = typer.Option(
        None, help="Maximum numbers of job to launch (default: all)"
    ),
):
    """Launch category prediction jobs on all products without categories in
    DB."""
    import tqdm
    from openfoodfacts.dataset import ProductDataset

    from robotoff.models import Prediction, db
    from robotoff.settings import DATASET_DIR
    from robotoff.utils import get_logger
    from robotoff.workers.queues import enqueue_job, low_queue
    from robotoff.workers.tasks.common import add_category_insight_job

    logger = get_logger()
    # Download the latest dump of the dataset, cache it in DATASET_DIR
    ds = ProductDataset(force_download=True, download_newer=True, cache_dir=DATASET_DIR)

    # The category detector only works for food products
    server_type = ServerType.off

    logger.info("Fetching products without categories in DB...")
    with db:
        barcode_with_categories = set(
            barcode
            for (barcode,) in Prediction.select(Prediction.barcode)
            .distinct()
            .where(
                Prediction.server_type == server_type.name,
                Prediction.type == PredictionType.category.name,
            )
            .tuples()
            .limit(limit)
        )
    logger.info(
        "%d products with categories already in DB", len(barcode_with_categories)
    )
    seen: set[str] = set()
    added = 0
    for product in tqdm.tqdm(ds, desc="products"):
        barcode = product.get("code")
        if not barcode or barcode in seen or barcode in barcode_with_categories:
            continue
        seen.add(barcode)
        # Enqueue a job to predict category for this product
        enqueue_job(
            add_category_insight_job,
            low_queue,
            job_kwargs={"result_ttl": 0},
            product_id=ProductIdentifier(barcode, server_type),
            triton_uri=triton_uri,
        )
        added += 1

    logger.info("%d jobs added", added)


@app.command()
def run_object_detection_model(
    server_type: ServerType = typer.Option(
        ServerType.off, help="Server type of the product"
    ),
    model_name: ObjectDetectionModel = typer.Argument(
        ..., help="Name of the object detection model"
    ),
    input_path: Optional[Path] = typer.Option(
        None,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="text file with image URLs to run object detection on. "
        "If null, a query is performed in DB to fetch images without image predictions "
        "for the specified model.",
    ),
    limit: Optional[int] = typer.Option(None, help="Maximum numbers of job to launch"),
    triton_uri: Optional[str] = typer.Option(
        None,
        help="URI of the Triton Inference Server to use. If not provided, the default value from settings is used.",
    ),
):
    """Launch object detection model jobs on all missing images (images
    without an ImagePrediction item for this model) in DB."""
    from typing import Callable
    from urllib.parse import urlparse

    import tqdm
    from openfoodfacts.images import extract_barcode_from_url
    from peewee import JOIN

    from robotoff.models import ImageModel, ImagePrediction, db
    from robotoff.off import generate_image_url
    from robotoff.utils import text_file_iter
    from robotoff.workers.queues import enqueue_job, low_queue
    from robotoff.workers.tasks.import_image import (
        run_logo_object_detection,
        run_nutriscore_object_detection,
        run_nutrition_table_object_detection,
    )

    if model_name == ObjectDetectionModel.universal_logo_detector:
        func: Callable = run_logo_object_detection
    elif model_name == ObjectDetectionModel.nutrition_table:
        func = run_nutrition_table_object_detection
    elif model_name == ObjectDetectionModel.nutriscore:
        func = run_nutriscore_object_detection
    else:
        raise ValueError(f"unsupported model: {model_name}")

    if input_path:
        image_urls = list(text_file_iter(input_path))

        for image_url in image_urls:
            parsed_url = urlparse(image_url)
            if not parsed_url.netloc or not parsed_url.scheme:
                raise ValueError(f"invalid image URL: {image_url}")

        if limit:
            image_urls = image_urls[:limit]

    else:
        with db:
            query = (
                ImageModel.select(ImageModel.barcode, ImageModel.image_id)
                .join(
                    ImagePrediction,
                    JOIN.LEFT_OUTER,
                    on=(
                        (ImagePrediction.image_id == ImageModel.id)
                        & (ImagePrediction.model_name == model_name.name)
                    ),
                )
                .where(
                    (ImageModel.server_type == server_type.name)
                    & ImagePrediction.model_name.is_null()
                    & (ImageModel.deleted == False),  # noqa: E712
                )
                .tuples()
            )
            if limit:
                query = query.limit(limit)
            image_urls = [
                generate_image_url(ProductIdentifier(barcode, server_type), image_id)
                for barcode, image_id in query
                if barcode.isdigit()
            ]

    if typer.confirm(f"{len(image_urls)} jobs are going to be launched, confirm?"):
        for image_url in tqdm.tqdm(image_urls, desc="image"):
            barcode = extract_barcode_from_url(image_url)
            if barcode is None:
                raise RuntimeError()
            enqueue_job(
                func,
                low_queue,
                job_kwargs={"result_ttl": 0},
                product_id=ProductIdentifier(barcode, server_type),
                image_url=image_url,
                triton_uri=triton_uri,
            )


@app.command()
def rerun_import_all_images(
    server_type: Optional[ServerType] = typer.Option(
        None, help="Server type of the product"
    ),
    limit: Optional[int] = typer.Option(
        None, help="the maximum number of images to process, defaults to None (all)"
    ),
    flags: list[ImportImageFlag] = typer.Option(
        None, help="Flags to use for image import"
    ),
):
    """Rerun full image import on all images in DB.

    This includes launching all ML models and insight extraction from the image and
    associated OCR. To control which tasks are rerun, use the --flags option.
    """
    from robotoff.workers.tasks.import_image import (
        rerun_import_all_images as _rerun_import_all_images,
    )

    flags_ = flags or None
    count = _rerun_import_all_images(
        limit=limit, server_type=server_type, flags=flags_, return_count=True
    )
    message = (
        f"rerunning full image import on {count} images, confirm?"
        if flags_ is None
        else f"running following tasks ({', '.join(flag.name for flag in flags_)}) on {count} images, confirm?"
    )
    if typer.confirm(message):
        _rerun_import_all_images(limit=limit, server_type=server_type, flags=flags_)
    typer.echo("The task was successfully scheduled.")


@app.command()
def run_nutrition_extraction(
    image_url: str = typer.Argument(
        ..., help="URL of the image to run nutrition extraction on"
    ),
    triton_uri: Optional[str] = typer.Option(
        None,
        help="URI of the Triton Inference Server to use. If not provided, the default value from settings is used.",
    ),
    model_version: Optional[str] = typer.Option(
        None, help="Version of the model to use, defaults to the latest"
    ),
) -> None:
    """Run nutrition extraction on a product image.

    The image URL should be an Open Food Facts image URL, e.g.
    https://images.openfoodfacts.org/images/products/327/408/000/5003/3.jpg

    The OCR JSON is expected to be available at the same URL with a `.json`
    extension, e.g.
    https://images.openfoodfacts.org/images/products/327/408/000/5003/3.json

    Prediction is printed to stdout.
    """
    from typing import cast

    from openfoodfacts.ocr import OCRResult
    from PIL import Image
    from rich import print as pprint

    from robotoff.images import get_image_from_url
    from robotoff.prediction.nutrition_extraction import predict

    image = cast(Image.Image, get_image_from_url(image_url))
    ocr_result = cast(OCRResult, OCRResult.from_url(image_url.replace(".jpg", ".json")))
    prediction = predict(
        image, ocr_result, model_version=model_version, triton_uri=triton_uri
    )
    if prediction is not None:
        pprint(prediction)
    else:
        pprint("No prediction")


@app.command()
def init_elasticsearch() -> None:
    """This command is used for index creation."""
    from robotoff.elasticsearch import ElasticsearchExporter, get_es_client
    from robotoff.utils import get_logger

    logger = get_logger()

    logger.info("Initializing Elasticsearch...")
    logger.info("Creating indices...")
    es_exporter = ElasticsearchExporter(get_es_client())
    es_exporter.load_all_indices()
    logger.info("Elasticsearch initialization finished")


@app.command()
def add_logo_to_ann(
    server_type: ServerType = typer.Option(
        ServerType.off, help="Server type of the logos"
    ),
    sleep_time: float = typer.Option(
        0.0, help="Time to sleep between each query (in s)"
    ),
    existing_ids_path: Optional[Path] = typer.Argument(
        None,
        file_okay=True,
        dir_okay=False,
        help="Path of the plain text file containing logo IDs (one ID per line). If not provided, "
        "existing IDs will be fetched from Elasticsearch.",
    ),
) -> None:
    """Index all missing logos in Elasticsearch ANN index."""
    import logging
    import time

    import tqdm
    from elasticsearch.helpers import BulkIndexError
    from more_itertools import chunked
    from playhouse.postgres_ext import ServerSide

    from robotoff.elasticsearch import get_es_client
    from robotoff.logos import add_logos_to_ann, get_stored_logo_ids
    from robotoff.models import LogoEmbedding, db
    from robotoff.utils import get_logger, text_file_iter

    logger = get_logger()
    logging.getLogger("elastic_transport.transport").setLevel(logging.WARNING)

    es_client = get_es_client()
    if existing_ids_path is not None and existing_ids_path.is_file():
        seen = set(int(x) for x in text_file_iter(existing_ids_path))
    else:
        seen = get_stored_logo_ids(es_client)
    logger.info("Number of existing logos: %d", len(seen))

    added = 0

    with db.connection_context():
        logger.info("Fetching logo embedding to index...")
        query = LogoEmbedding.select().objects()
        logo_embedding_iter = (
            logo_embedding
            for logo_embedding in tqdm.tqdm(ServerSide(query), desc="logo")
            if logo_embedding.logo_id not in seen
        )

        for logo_embedding_batch in chunked(logo_embedding_iter, 500):
            try:
                add_logos_to_ann(es_client, logo_embedding_batch, server_type)
                added += len(logo_embedding_batch)
            except BulkIndexError as e:
                logger.info("Request error during logo addition to ANN", exc_info=e)

            if sleep_time:
                time.sleep(sleep_time)

    logger.info("%s embeddings indexed", added)


@app.command()
def refresh_logo_nearest_neighbors(
    day_offset: int = typer.Option(7, help="Number of days since last refresh", min=1),
    batch_size: int = typer.Option(500, help="Number of logos to process at once"),
    server_type: ServerType = typer.Option(ServerType.off, help="Server type"),
):
    """Refresh each logo nearest neighbors if the last refresh is more than
    `day_offset` days old."""
    import logging

    from robotoff.logos import refresh_nearest_neighbors
    from robotoff.models import db
    from robotoff.utils import get_logger

    logger = get_logger()
    logging.getLogger("elastic_transport.transport").setLevel(logging.WARNING)

    logger.info("Starting refresh of logo nearest neighbors")

    with db.connection_context():
        refresh_nearest_neighbors(server_type, day_offset, batch_size)


@app.command()
def import_logo_embeddings(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="HDF5 file containing logo embeddings. Two HDF5 datasets are expected: "
        "one containing the embeddings and one containing the logo IDs.",
    ),
    embedding_dataset_name: str = typer.Option(
        "embedding",
        help="name of the HDF5 dataset corresponding to logo embedding in the HDF5 file",
    ),
    logo_id_dataset_name: str = typer.Option(
        "logo_id",
        help="name of the HDF5 dataset corresponding to logo ID in the HDF5 file",
    ),
    update_if_exists: bool = typer.Option(
        False,
        help="if the logo embedding already exists in database, update it if True, otherwise ignore it.",
    ),
) -> None:
    """Import logo embeddings in DB from an HDF5 file."""
    import h5py
    import numpy as np
    import tqdm
    from more_itertools import chunked

    from robotoff.models import LogoAnnotation, LogoEmbedding, db
    from robotoff.utils import get_logger

    logger = get_logger()
    logger.info("Importing logo embeddings from %s", input_path)
    logger.info(
        "Options: update_if_exists=%s, embedding_dataset_name=%s, logo_id_dataset_name=%s",
        update_if_exists,
        embedding_dataset_name,
        logo_id_dataset_name,
    )

    with db:
        existing_logo_ids = set(
            x[0] for x in LogoAnnotation.select(LogoAnnotation.id).tuples().iterator()
        )
        existing_embedding_logo_ids = set(
            x[0]
            for x in LogoEmbedding.select(LogoEmbedding.logo_id).tuples().iterator()
        )

    imported = 0
    updated = 0
    not_found = 0
    with h5py.File(input_path, "r") as f:
        embeddings = f[embedding_dataset_name]
        logo_ids = f[logo_id_dataset_name]
        non_zero_indexes = np.flatnonzero(logo_ids[:])
        max_index = int(non_zero_indexes[-1])
        logger.info("Number of embeddings in HDF5 file: %d", max_index)

        pbar = tqdm.tqdm(range(max_index), desc="embedding")
        with db.connection_context():
            for batch_indices in chunked(pbar, 1000):
                with db.atomic():
                    for i in batch_indices:
                        embedding = embeddings[i]
                        logo_id = int(logo_ids[i])
                        assert embedding.shape[0] == 512
                        assert embedding.dtype == np.float32
                        assert not np.all(embedding == 0.0)
                        logo_id = int(logo_ids[i])
                        if logo_id in existing_logo_ids:
                            if logo_id not in existing_embedding_logo_ids:
                                LogoEmbedding.create(
                                    logo_id=logo_id, embedding=embedding.tobytes()
                                )
                                existing_embedding_logo_ids.add(logo_id)
                                imported += 1
                            elif update_if_exists:
                                updated += (
                                    LogoEmbedding.update(
                                        {"embedding": embedding.tobytes()}
                                    )
                                    .where(LogoEmbedding.logo_id == logo_id)
                                    .execute()
                                )
                        else:
                            not_found += 1
                    pbar.postfix = f"imported: {imported}, updated: {updated}, not found: {not_found}"
        pbar.close()

    logger.info(
        "embeddings: %d imported, %d updated, %d not found",
        imported,
        updated,
        not_found,
    )


@app.command()
def import_logos(
    data_path: Path = typer.Argument(
        ...,
        help="Path to the JSONL file containing data to import",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    batch_size: int = typer.Option(
        1024, help="Number of predictions to insert in DB in a single SQL transaction"
    ),
    server_type: ServerType = typer.Option(ServerType.off, help="Server type"),
) -> None:
    """Import object detection predictions for universal-logo-detector model.

    This command creates ImagePrediction and associated LogoAnnotation, but do
    not generate logo embedding or index the embeddings in the ANN index.

    Each JSON item should have the following field:

    - barcode: the barcode of the product
    - image_id: the image ID ("1", "2",...), must be a digit
    - result: a list of dict, containing:
        - score: the confidence score (float)
        - bounding_box: a list with 4 elements, corresponding to the
          normalized detected bounding box
        - label: either `label` or `brand`

    """
    from robotoff.cli import logos
    from robotoff.models import db
    from robotoff.prediction.object_detection import MODELS_CONFIG
    from robotoff.utils import get_logger

    logger = get_logger()
    logger.info("Starting logo import...")

    with db.connection_context():
        imported = logos.import_logos(
            data_path,
            ObjectDetectionModel.universal_logo_detector.value,
            MODELS_CONFIG[ObjectDetectionModel.universal_logo_detector].model_version,
            batch_size,
            server_type,
        )

    logger.info("%s image predictions created", imported)


@app.command()
def export_logos(
    output: Path = typer.Argument(
        ...,
        help="Path to the output file, can either have .jsonl or .jsonl.gz as "
        "extension",
    ),
) -> None:
    """Export all information about logo in DB necessary to generate logo
    crops."""
    from robotoff.models import LogoAnnotation, db
    from robotoff.utils import dump_jsonl

    with db:
        query = LogoAnnotation.select(
            LogoAnnotation.id,
            LogoAnnotation.index,
            LogoAnnotation.bounding_box,
            LogoAnnotation.score,
            LogoAnnotation.annotation_type,
            LogoAnnotation.annotation_value,
            LogoAnnotation.annotation_value_tag,
            LogoAnnotation.taxonomy_value,
            LogoAnnotation.username,
            LogoAnnotation.source_image,
            LogoAnnotation.barcode,
        )
        dump_jsonl(output, query.dicts().iterator())


@app.command()
def pprint_ocr_result(
    uri: str = typer.Argument(..., help="URI of the image or OCR"),
) -> None:
    """Pretty print OCR result."""
    import sys

    import orjson
    from openfoodfacts.ocr import OCRResult

    from robotoff.utils import get_logger, http_session

    logger = get_logger()

    if uri.endswith(".jpg"):
        uri = uri.replace(".jpg", ".json")

    logger.info("displaying OCR result %s", uri)

    if uri.startswith("http"):
        ocr_result = OCRResult.from_url(uri, http_session)
    else:
        with open(uri, "rb") as f:
            data = orjson.loads(f.read())
            ocr_result = OCRResult.from_json(data)

    if ocr_result is None:
        logger.info("error while downloading %s", uri)
        sys.exit(0)

    if ocr_result.full_text_annotation is None:
        logger.info("no full text annotation available")
        sys.exit(0)
    ocr_result.pprint()


@app.command()
def generate_ocr_result(
    image_url: str = typer.Argument(..., help="URL of the image"),
    output_dir: Path = typer.Argument(
        ...,
        file_okay=False,
        dir_okay=True,
        help="Directory where the OCR JSON should be saved",
    ),
    overwrite: bool = typer.Option(
        False, help="Overwrite the output file if it already exists"
    ),
) -> None:
    import os

    import orjson

    from robotoff.cli.ocr import run_ocr_on_image
    from robotoff.off import get_source_from_url
    from robotoff.utils import get_logger, http_session

    logger = get_logger()
    API_KEY = os.environ["GOOGLE_CLOUD_VISION_API_KEY"]

    output_dir.mkdir(parents=True, exist_ok=True)
    source_image_path = Path(get_source_from_url(image_url))
    output_file = output_dir / (
        str(source_image_path.parent).replace("/", "_")[1:]
        + f"_{source_image_path.stem}.json"
    )
    if output_file.is_file() and not overwrite:
        logger.info("Skipping %s, file already exists", output_file)
        return

    logger.info("Downloading image %s", image_url)
    r = http_session.get(image_url)
    r.raise_for_status()

    logger.info("Generating OCR result")
    response = run_ocr_on_image(r.content, API_KEY)

    with open(output_file, "wb") as f:
        f.write(orjson.dumps(response))

    pprint_ocr_result(str(output_file))


@app.command()
def migrate_db():
    """Run unapplied DB migrations."""
    from robotoff.models import db, run_migration
    from robotoff.utils import get_logger

    get_logger()

    with db.connection_context():
        run_migration()


@app.command()
def create_migration(
    name: str = typer.Argument(..., help="name of the migration"),
    auto: bool = typer.Option(
        False,
        help="Scan sources and create db migrations automatically. Supports autodiscovery.",
    ),
):
    """Create a new migration file using peewee_migrate."""
    from peewee_migrate import Router

    from robotoff import settings
    from robotoff.models import db

    with db.connection_context():
        router = Router(db, migrate_dir=settings.MIGRATE_DIR)
        router.create(name, auto=auto)


@app.command()
def launch_spellcheck_batch_job(
    min_fraction_unknown: float = 0,
    max_fraction_unknown: float = 0.4,
    limit: int = 10_000,
) -> None:
    """Launch a spellcheck batch job."""

    from robotoff.batch import (
        launch_spellcheck_batch_job as _launch_spellcheck_batch_job,
    )
    from robotoff.utils import get_logger

    get_logger()
    _launch_spellcheck_batch_job(
        min_fraction_unknown=min_fraction_unknown,
        max_fraction_unknown=max_fraction_unknown,
        limit=limit,
    )


@app.command()
def import_batch_job_predictions(batch_dir: str) -> None:
    """Import predictions from batch job.

    Currently, only ingredients spellcheck predictions are supported.
    """
    from robotoff.batch import BatchJobType, import_batch_predictions
    from robotoff.utils.logger import get_logger

    get_logger()

    import_batch_predictions(BatchJobType.ingredients_spellcheck, batch_dir)


@app.command()
def launch_normalize_barcode_job(
    batch_size: int = 100_000,
    launch_prediction: bool = True,
    launch_insight: bool = True,
    launch_image: bool = True,
) -> None:
    from openfoodfacts.barcode import normalize_barcode
    from openfoodfacts.images import generate_image_path
    from peewee import fn

    from robotoff.models import ImageModel, Prediction, ProductInsight, db
    from robotoff.utils import get_logger

    logger = get_logger()
    logger.info("Starting barcode normalization job")

    with db.connection_context():
        if launch_prediction:
            updated = 0
            min_id = 0
            max_id = Prediction.select(fn.MAX(Prediction.id)).scalar()
            with db.atomic() as tsx:
                while min_id < max_id:
                    prediction = None
                    for prediction in (
                        Prediction.select()
                        .where(Prediction.id >= min_id)
                        .order_by(Prediction.id.asc())
                        .limit(batch_size)
                    ):
                        barcode = normalize_barcode(prediction.barcode)
                        source_image = (
                            generate_image_path(
                                prediction.barcode, Path(prediction.source_image).stem
                            )
                            if prediction.source_image
                            else None
                        )
                        is_updated = (barcode != prediction.barcode) or (
                            source_image != prediction.source_image
                        )
                        if is_updated:
                            prediction.barcode = barcode
                            prediction.source_image = source_image
                            prediction.save()
                            updated += 1

                    tsx.commit()
                    logger.info(
                        "Current ID: %s, Updated %d predictions", min_id, updated
                    )
                    if prediction is not None:
                        min_id = prediction.id
                    else:
                        break
                logger.info("Updated %d predictions", updated)

        if launch_insight:
            updated = 0
            min_id = ProductInsight.select(fn.MIN(ProductInsight.timestamp)).scalar()
            max_id = ProductInsight.select(fn.MAX(ProductInsight.timestamp)).scalar()
            with db.atomic() as tsx:
                while min_id < max_id:
                    insight = None
                    for insight in (
                        ProductInsight.select()
                        .where(ProductInsight.timestamp >= min_id)
                        .order_by(ProductInsight.timestamp.asc())
                        .limit(batch_size)
                    ):
                        barcode = normalize_barcode(insight.barcode)
                        source_image = (
                            generate_image_path(
                                insight.barcode, Path(insight.source_image).stem
                            )
                            if insight.source_image
                            else None
                        )
                        is_updated = (barcode != insight.barcode) or (
                            source_image != insight.source_image
                        )
                        if is_updated:
                            insight.barcode = barcode
                            insight.source_image = source_image
                            insight.save()
                            updated += 1

                    tsx.commit()
                    logger.info("Current ID: %s, Updated %d insights", min_id, updated)
                    if insight is not None:
                        min_id = insight.timestamp
                    else:
                        break
                logger.info("Updated %d insights", updated)

        if launch_image:
            updated = 0
            min_id = ImageModel.select(fn.MIN(ImageModel.id)).scalar()
            max_id = ImageModel.select(fn.MAX(ImageModel.id)).scalar()
            with db.atomic() as tsx:
                while min_id < max_id:
                    image = None
                    for image in (
                        ImageModel.select()
                        .where(ImageModel.id >= min_id)
                        .order_by(ImageModel.id.asc())
                        .limit(batch_size)
                    ):
                        barcode = normalize_barcode(image.barcode)
                        source_image = (
                            generate_image_path(
                                image.barcode, Path(image.source_image).stem
                            )
                            if image.source_image
                            else None
                        )
                        is_updated = (barcode != image.barcode) or (
                            source_image != image.source_image
                        )
                        if is_updated:
                            image.barcode = barcode
                            image.source_image = source_image
                            image.save()
                            updated += 1

                    tsx.commit()
                    logger.info("Current ID: %s, Updated %d images", min_id, updated)
                    if image is not None:
                        min_id = image.id
                    else:
                        break
                logger.info("Updated %d images", updated)


@app.command()
def update_insight_with_image_field() -> None:
    """Refresh the `with_image` field of all insights."""
    import tqdm

    from robotoff.models import ImageModel, ProductInsight, db
    from robotoff.types import InsightType
    from robotoff.utils.logger import get_logger

    get_logger()

    with db.connection_context():
        with db.atomic() as tsx:
            for insight in tqdm.tqdm(
                ProductInsight.select()
                .where(
                    ProductInsight.type.in_(
                        [InsightType.brand.name, InsightType.category.name]
                    ),
                    # Only non-annotated insights
                    ProductInsight.annotation.is_null(True),
                )
                .iterator(),
                desc="insight",
            ):
                has_image = (
                    ImageModel.select()
                    .where(
                        (ImageModel.barcode == insight.barcode)
                        & (ImageModel.server_type == insight.server_type)
                        & (ImageModel.deleted == False)  # noqa: E712
                    )
                    .exists()
                )
                if insight.with_image != has_image:
                    insight.with_image = has_image
                    insight.save()
                    tsx.commit()

            ProductInsight.update(
                with_image=ProductInsight.source_image.is_null(False)
            ).where(
                ProductInsight.type.not_in(
                    [InsightType.category.name, InsightType.brand.name]
                ),
            ).execute()


def main() -> None:
    app()
