from typing import List

import pandas as pd

from robotoff.insights.importer import import_insights
from robotoff.batch import BatchJobType, GoogleStorageBucketForBatchJob
from robotoff.types import Prediction, PredictionType
from robotoff.models import db
from robotoff.utils import get_logger
from robotoff.types import ServerType


LOGGER = get_logger(__name__)

BATCH_JOB_TYPE_TO_FEATURES = {
    BatchJobType.ingredients_spellcheck: {
        "barcode": "code",
        "value": "correction",
        "value_tag": "lang", 
    },
}

BATCH_JOB_TYPE_TO_PREDICTION_TYPE = {
    BatchJobType.ingredients_spellcheck: PredictionType.ingredient_spellcheck,
}

PREDICTOR_VERSION = "2"


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

    :param f: Readable object. Should be a parquet file.
    :type f: io.BufferedReader
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
                predictor="llm",
            )
        )
    return predictions
