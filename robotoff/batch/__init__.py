import base64
import datetime
import json
import os
import tempfile
from pathlib import Path

import duckdb

from robotoff import settings
from robotoff.insights.importer import import_insights
from robotoff.models import db
from robotoff.types import BatchJobType, Prediction, PredictionType, ServerType
from robotoff.utils import get_logger

from .buckets import fetch_dataframe_from_gcs, upload_file_to_gcs
from .launch import GoogleBatchJobConfig, launch_job

logger = get_logger(__name__)


def import_batch_predictions(job_type: BatchJobType) -> None:
    """Import batch predictions once the job finished.
    Need to be updated if different batch jobs are added.
    """
    if job_type is BatchJobType.ingredients_spellcheck:
        import_spellcheck_batch_predictions()
    else:
        raise NotImplementedError(f"Batch job type {job_type} not implemented.")


def import_spellcheck_batch_predictions() -> None:
    """Import spellcheck predictions from remote storage."""
    # Init
    BUCKET_NAME = "robotoff-spellcheck"
    SUFFIX_POSTPROCESS = "data/postprocessed_data.parquet"
    PREDICTION_TYPE = PredictionType.ingredient_spellcheck
    # We increment to allow import_insights to create a new version
    PREDICTOR_VERSION = (
        "llm-v1" + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    )
    PREDICTOR = "fine-tuned-mistral-7b"
    SERVER_TYPE = ServerType.off

    check_google_credentials()

    df = fetch_dataframe_from_gcs(bucket_name=BUCKET_NAME, suffix=SUFFIX_POSTPROCESS)
    logger.debug(
        "Batch data downloaded from bucket %s/%s", BUCKET_NAME, SUFFIX_POSTPROCESS
    )
    logger.info("Number of rows in the batch data: %s", len(df))

    # Generate predictions
    predictions = []
    for _, row in df.iterrows():
        predictions.append(
            Prediction(
                type=PREDICTION_TYPE,
                data={"original": row["text"], "correction": row["correction"]},
                value_tag=row["lang"],
                barcode=row["code"],
                predictor_version=PREDICTOR_VERSION,
                predictor=PREDICTOR,
                automatic_processing=False,
            )
        )
    # Store predictions and insights
    with db:
        import_results = import_insights(
            predictions=predictions, server_type=SERVER_TYPE
        )
    logger.info("Batch import results: %s", import_results)


def launch_spellcheck_batch_job(
    min_fraction_known: float = 0,
    max_fraction_known: float = 0.4,
    limit: int = 10_000,
) -> None:
    """Launch spellcheck batch job."""
    # Init
    job_name = "ingredients-spellcheck"
    batch_job_config_path = (
        settings.BATCH_JOB_CONFIG_DIR / "job_configs/spellcheck.yaml"
    )
    bucket_name = "robotoff-batch"
    input_file_dir = f"{job_name}/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{settings._get_tld()}"
    input_file_path = f"{input_file_dir}/preprocessed_data.parquet"
    output_file_path = f"{input_file_dir}/postprocessed_data.parquet"

    check_google_credentials()

    logger.info("Extract batch from dataset.")
    # Extract data from dataset
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = os.path.join(tmp_dir, "batch_data.parquet")
        extract_from_dataset(
            file_path,
            min_fraction_known=min_fraction_known,
            max_fraction_known=max_fraction_known,
            limit=limit,
        )
        # Upload the extracted file to the bucket
        upload_file_to_gcs(
            file_path=file_path, bucket_name=bucket_name, suffix=input_file_path
        )
        logger.debug("File uploaded to the bucket %s/%s", bucket_name, input_file_path)

    # Launch batch job
    batch_job_config = GoogleBatchJobConfig.init(
        job_name=job_name,
        config_path=batch_job_config_path,
        env_variables={
            "BUCKET_NAME": bucket_name,
            "BATCH_JOB_KEY": os.environ["BATCH_JOB_KEY"],
            "WEBHOOK_URL": f"{settings.BaseURLProvider.robotoff()}/api/v1/batch/import",
            "INPUT_FILE_PATH": input_file_path,
            "OUTPUT_FILE_PATH": output_file_path,
        },
    )
    logger.info("Batch job config: %s", batch_job_config)
    batch_job = launch_job(batch_job_config=batch_job_config)
    logger.info("Batch job succesfully launched. Batch job %s", batch_job)


def extract_from_dataset(
    output_file_path: str,
    dataset_path: Path = settings.JSONL_DATASET_PATH,
    min_fraction_known: float = 0,
    max_fraction_known: float = 0.4,
    limit: int = 10_000,
) -> None:
    """Using SQL queries, extract data from the JSONL dataset and save it as a parquet
    file.

    :param output_file_path: Path to save the extracted data.
    :param dataset_path: Compressed jsonl database, defaults to
        settings.JSONL_DATASET_PATH
    :param min_fraction_known: Select products min fraction of known ingredients above
        this, defaults to 0
    :param max_fraction_known: Select products max fraction of known ingredients below
        this, defaults to 0.4
    :param limit: Maximal number of products to extract, defaults to 10_000
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path {str(dataset_path)} not found.")

    query = f"""SELECT
        code,
        ingredients_text AS text,
        product_name,
        lang,
        popularity_key,
        (CAST(unknown_ingredients_n AS FLOAT) / CAST(ingredients_n AS FLOAT)) AS fraction
        FROM read_ndjson('{dataset_path}', ignore_errors=True)
        WHERE ingredients_text NOT LIKE ''
        AND fraction > {min_fraction_known} AND fraction <= {max_fraction_known}
        ORDER BY popularity_key DESC
        LIMIT {limit};"""
    logger.debug(f"Query used to extract batch from dataset: {query}")
    duckdb.sql(query).write_parquet(output_file_path)
    logger.debug(f"Batch data succesfully extracted and saved at {output_file_path}")


def check_google_credentials() -> None:
    """Create google credentials from variable if doesn't exist."""
    credentials_path = settings.PROJECT_DIR / "credentials/google/credentials.json"
    if not credentials_path.is_file():
        logger.info(
            "No google credentials found at %s. Creating credentials from GOOGLE_CREDENTIALS.",
            credentials_path,
        )
        credentials_path.parent.mkdir(parents=True, exist_ok=True)
        credentials_base64 = os.environ["GOOGLE_CREDENTIALS"]
        credentials = json.loads(base64.b64decode(credentials_base64).decode("utf-8"))
        with open(credentials_path, "w") as f:
            json.dump(credentials, f, indent=4)
