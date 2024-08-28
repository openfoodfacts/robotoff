import tempfile
from typing import List

import pandas as pd

from robotoff.utils import get_logger
from robotoff.types import (
    BatchJobType,
    Prediction, 
    ServerType
)
from robotoff.models import db
from robotoff.insights.importer import import_insights

from .launch import (
    GoogleBatchJob,
    GoogleBatchJobConfig,
)
from .extraction import (
    BatchExtraction,
)
from .buckets import (
    GoogleStorageBucketForBatchJob,
)
from .types import (
    BATCH_JOB_TYPE_TO_FEATURES,
    BATCH_JOB_TYPE_TO_PREDICTION_TYPE,
)


LOGGER = get_logger(__name__)

PREDICTOR_VERSION = "1" #TODO: shard HF model version? instead of manual change?

PREDICTOR = "llm"


def launch_batch_job(job_type: BatchJobType) -> None:
    """Launch a batch job.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        BatchExtraction.extract_from_dataset(
            job_type=job_type,
            output_dir=tmp_dir,
        )
        if not BatchExtraction.extracted_file_path:
            raise ValueError("The extracted file was not found.")
        LOGGER.debug(f"Batch data succesfully extracted and saved at {BatchExtraction.extracted_file_path}")

        # Upload the extracted file to the bucket
        bucket_handler = GoogleStorageBucketForBatchJob.from_job_type(job_type)
        bucket_handler.upload_file(file_path=BatchExtraction.extracted_file_path)
        LOGGER.debug(f"File uploaded to the bucket {bucket_handler.bucket}/{bucket_handler.suffix_preprocess}")

    # Launch batch job
    batch_job_config = GoogleBatchJobConfig.init(job_type=job_type)
    batch_job = GoogleBatchJob.launch_job(batch_job_config=batch_job_config)
    LOGGER.info(f"Batch job succesfully launched. Batch job name: {batch_job.name}.")


def import_batch_predictions(job_type: BatchJobType) -> None:
    """Import predictions from remote storage.
    """
    bucket_handler = GoogleStorageBucketForBatchJob.from_job_type(job_type)
    LOGGER.debug(f"Batch data downloaded from bucket {bucket_handler.bucket}/{bucket_handler.suffix_postprocess}")
    df = bucket_handler.download_file()
    predictions = _generate_predictions_from_batch(df, job_type)
    with db:
        import_results = import_insights(
            predictions=predictions,
            server_type=ServerType.off
        )
    LOGGER.info(f"Batch import results: {repr(import_results)}.")


def _generate_predictions_from_batch(
    df: pd.DataFrame, 
    job_type: BatchJobType
) -> List[Prediction]:
    """From a file imported from google storage, generate predictions depending on the job type.

    :param df: Post-processed dataset
    :type df: pd.DataFrame
    :param job_type: Batch job type.
    :type job_type: BatchJobType
    :rtype: Iterable[Prediction]
    :yield: Predictions.
    :rtype: Iterator[Prediction]
    """
    predictions = []
    features_dict = BATCH_JOB_TYPE_TO_FEATURES[job_type]
    prediction_type = BATCH_JOB_TYPE_TO_PREDICTION_TYPE[job_type]
    for _, row in df.iterrows():
        predictions.append(
            Prediction(
                type=prediction_type,
                value=row[features_dict["value"]],
                value_tag=row[features_dict["value_tag"]],
                barcode=row[features_dict["barcode"]],
                predictor_version=PREDICTOR_VERSION,
                predictor=PREDICTOR,
            )
        )
    return predictions

