from robotoff.types import BatchJobType, PredictionType
from robotoff import settings


# Bucket structure to enable the batch job to load and upload data
BATCH_JOB_TYPE_TO_BUCKET = {
    BatchJobType.ingredients_spellcheck: {
        "bucket": "robotoff-spellcheck", 
        "suffix_preprocess": "data/preprocessed_data.parquet",
        "suffix_postprocess": "data/postprocessed_data.parquet",
    },
}

# Paths batch job config files
BATCH_JOB_TYPE_TO_CONFIG_PATH = {
    BatchJobType.ingredients_spellcheck: settings.BATCH_JOB_CONFIG_DIR / "job_configs/spellcheck.yaml",
}

BATCH_JOB_TYPE_TO_QUERY_FILE_PATH = {
    BatchJobType.ingredients_spellcheck: settings.BATCH_JOB_CONFIG_DIR / "sql/spellcheck.sql",
}

# Mapping between batch job type and prediction type
BATCH_JOB_TYPE_TO_PREDICTION_TYPE = {
    BatchJobType.ingredients_spellcheck: PredictionType.ingredient_spellcheck,
}

# Column names in the processed batch of data
BATCH_JOB_TYPE_TO_FEATURES = {
    BatchJobType.ingredients_spellcheck: {
        "barcode": "code",
        "value": "correction",
        "value_tag": "lang", 
    },
}
