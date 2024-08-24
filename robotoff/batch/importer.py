import io
from typing import Iterator

import pandas as pd

from robotoff.batch import BatchJobType
from robotoff.types import Prediction, PredictionType


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

PREDICTOR_VERSION = "1"


def generate_predictions_from_batch(
    f: io.BufferedReader, 
    job_type: BatchJobType
) -> Iterator[Prediction]:
    """From a file imported from google storage, generate predictions depending on the job type.

    :param f: Readable object. Should be a parquet file.
    :type f: io.BufferedReader
    :param job_type: Batch job type.
    :type job_type: BatchJobType
    :rtype: Iterable[Prediction]
    :yield: Predictions.
    :rtype: Iterator[Prediction]
    """
    features_dict = BATCH_JOB_TYPE_TO_FEATURES[job_type]
    prediction_type = BATCH_JOB_TYPE_TO_PREDICTION_TYPE[job_type]

    try:
        df = pd.read_parquet(f)
    except Exception as e:
        raise ValueError(f"Failed to read parquet file: {e}")
    
    for _, row in df.iterrows():
        yield Prediction(
            type=prediction_type,
            value=row[features_dict["value"]],
            value_tag=[features_dict["value_tag"]],
            barcode=row[features_dict["barcode"]],
            predictor_version=PREDICTOR_VERSION,
            predictor="llm",
        )
