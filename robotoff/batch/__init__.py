import base64
import datetime
import json
import os
import tempfile
from pathlib import Path

import duckdb
from more_itertools import chunked

from robotoff import settings
from robotoff.insights.importer import import_insights
from robotoff.models import db
from robotoff.prediction.langid import predict_lang
from robotoff.types import BatchJobType, Prediction, PredictionType, ServerType
from robotoff.utils import get_logger

from .buckets import fetch_dataframe_from_gcs, upload_file_to_gcs
from .launch import GoogleBatchJobConfig, launch_job

logger = get_logger(__name__)


def import_batch_predictions(job_type: BatchJobType, batch_dir: str) -> None:
    """Import batch predictions once the job finished.
    Need to be updated if different batch jobs are added.
    """
    if job_type is BatchJobType.ingredients_spellcheck:
        import_spellcheck_batch_predictions(batch_dir)
    else:
        raise NotImplementedError(f"Batch job type {job_type} not implemented.")


def import_spellcheck_batch_predictions(batch_dir: str) -> None:
    """Import spellcheck predictions from remote storage."""
    # Init
    bucket_name = "robotoff-batch"
    processed_file_path = f"{batch_dir}/postprocessed_data.parquet"

    check_google_credentials()

    df = fetch_dataframe_from_gcs(bucket_name=bucket_name, suffix=processed_file_path)
    logger.debug(
        "Batch data downloaded from bucket %s/%s", bucket_name, processed_file_path
    )
    logger.info("Number of rows in the batch data: %s", len(df))

    # We increment to allow import_insights to create a new version
    predictor_version = "llm-v1-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    for batch in chunked((row for _, row in df.iterrows()), 100):
        predictions = []
        for row in batch:
            lang_predictions = predict_lang(row["text"], k=1)
            lang, lang_confidence = lang_predictions[0].lang, (
                lang_predictions[0].confidence if lang_predictions else None
            )
            predictions.append(
                Prediction(
                    type=PredictionType.ingredient_spellcheck,
                    data={
                        "original": row["text"],
                        "correction": row["correction"],
                        "lang": lang,
                        "lang_confidence": lang_confidence,
                    },
                    value_tag=row["lang"],
                    barcode=row["code"],
                    predictor_version=predictor_version,
                    predictor="fine-tuned-mistral-7b",
                    automatic_processing=False,
                )
            )
        # Store predictions and insights
        with db:
            import_results = import_insights(
                predictions=predictions, server_type=ServerType.off
            )
        logger.info("Batch import results: %s", import_results)


def launch_spellcheck_batch_job(
    min_fraction_unknown: float = 0,
    max_fraction_unknown: float = 0.4,
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
            output_file_path=file_path,
            min_fraction_unknown=min_fraction_unknown,
            max_fraction_unknown=max_fraction_unknown,
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
    dataset_path: Path | None = None,
    min_fraction_unknown: float = 0,
    max_fraction_unknown: float = 0.4,
    limit: int = 10_000,
) -> None:
    """Using SQL queries, extract data from the JSONL dataset and save it as a parquet
    file.

    :param output_file_path: Path to save the extracted data.
    :param dataset_path: Path to the Parquet file, defaults to the ServerType.off
        dataset path defined in settings.PARQUET_DATASET_PATHS.
    :param min_fraction_unknown: Only select products that have a fraction of unknown
        ingredients above this threshold, defaults to 0
    :param max_fraction_unknown: Only select products that have a fraction of unknown
        ingredients below this threshold, defaults to 0.4
    :param limit: Maximal number of products to extract, defaults to 10_000
    """
    if dataset_path is None:
        dataset_path = settings.PARQUET_DATASET_PATHS[ServerType.off]

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path {str(dataset_path)} not found.")

    query = f"""
    SELECT
        code,
        list_filter(ingredients_text, x -> x.lang = 'main')[1].text AS text,
        lang,
        unknown_ingredients_n / ingredients_n AS fraction,
    FROM '{dataset_path}'
    WHERE list_contains(
        list_transform(ingredients_text, x -> x.lang),
        'main'
    )
        AND fraction > {min_fraction_unknown} AND fraction <= {max_fraction_unknown}
        AND text <> ''
    ORDER BY popularity_key DESC
    LIMIT {limit};
    """
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
