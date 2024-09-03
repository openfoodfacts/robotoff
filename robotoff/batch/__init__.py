import os
import tempfile

from robotoff import settings
from robotoff.insights.importer import import_insights
from robotoff.models import db
from robotoff.types import BatchJobType, Prediction, PredictionType, ServerType
from robotoff.utils import get_logger

from .buckets import fetch_dataframe_from_gcs, upload_file_to_gcs
from .extraction import extract_from_dataset
from .launch import GoogleBatchJobConfig, launch_job

logger = get_logger(__name__)


def launch_batch_job(job_type: BatchJobType) -> None:
    """Launch a batch job.
    Need to be updated if different batch jobs are added.
    """
    if job_type is BatchJobType.ingredients_spellcheck:
        launch_spellcheck_batch_job()
    else:
        raise NotImplementedError(f"Batch job type {job_type} not implemented.")


def import_batch_predictions(job_type: BatchJobType) -> None:
    """Import batch predictions once the job finished.
    Need to be updated if different batch jobs are added.
    """
    if job_type is BatchJobType.ingredients_spellcheck:
        import_spellcheck_batch_predictions()
    else:
        raise NotImplementedError(f"Batch job type {job_type} not implemented.")


def launch_spellcheck_batch_job() -> None:
    """Launch spellcheck batch job."""
    # Init
    JOB_NAME = "ingredients-spellcheck"
    QUERY_FILE_PATH = settings.BATCH_JOB_CONFIG_DIR / "sql/spellcheck.sql"
    BATCH_JOB_CONFIG_PATH = (
        settings.BATCH_JOB_CONFIG_DIR / "job_configs/spellcheck.yaml"
    )
    BUCKET_NAME = "robotoff-spellcheck"
    SUFFIX_PREPROCESS = "data/preprocessed_data.parquet"
    ENV_NAMES = ["BATCH_JOB_KEY"]

    logger.info("Extract batch from dataset.")
    # Extract data from dataset
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = os.path.join(tmp_dir, "batch_data.parquet")
        extract_from_dataset(QUERY_FILE_PATH, file_path)

        # Upload the extracted file to the bucket
        upload_file_to_gcs(
            file_path=file_path, bucket_name=BUCKET_NAME, suffix=SUFFIX_PREPROCESS
        )
        logger.debug(f"File uploaded to the bucket {BUCKET_NAME}/{SUFFIX_PREPROCESS}")

    # Launch batch job
    batch_job_config = GoogleBatchJobConfig.init(
        job_name=JOB_NAME,
        config_path=BATCH_JOB_CONFIG_PATH,
        env_names=ENV_NAMES,
    )
    logger.info("Batch job config: %s", batch_job_config)
    batch_job = launch_job(batch_job_config=batch_job_config)
    logger.info("Batch job succesfully launched. Batch job %s", batch_job)


def import_spellcheck_batch_predictions() -> None:
    """Import spellcheck predictions from remote storage."""
    # Init
    BUCKET_NAME = "robotoff-spellcheck"
    SUFFIX_POSTPROCESS = "data/postprocessed_data.parquet"
    PREDICTION_TYPE = PredictionType.ingredient_spellcheck
    PREDICTOR_VERSION = "1"  # TODO: shard HF model version instead of manual change?
    PREDICTOR = "fine-tuned-mistral-7b"
    SERVER_TYPE = ServerType.off

    df = fetch_dataframe_from_gcs(bucket_name=BUCKET_NAME, suffix=SUFFIX_POSTPROCESS)
    logger.debug(
        f"Batch data downloaded from bucket {BUCKET_NAME}/{SUFFIX_POSTPROCESS}"
    )

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
