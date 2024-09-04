import os
import tempfile
from pathlib import Path

import pytest

from robotoff import settings
from robotoff.batch import GoogleBatchJobConfig
from robotoff.batch.extraction import extract_from_dataset

DIR = Path(__file__).parent
SPELLCHECK_QUERY_FILE_PATH = settings.BATCH_JOB_CONFIG_DIR / "sql/spellcheck.sql"
SPELLCHECK_BATCH_JOB_CONFIG_PATH = (
    settings.BATCH_JOB_CONFIG_DIR / "job_configs/spellcheck.yaml"
)

os.environ["KEY"] = "value"


@pytest.mark.parametrize(
    "inputs",
    [
        ("ingredients-spellcheck", SPELLCHECK_BATCH_JOB_CONFIG_PATH, ["KEY"]),
    ],
)
def test_batch_job_config_file(inputs):
    "Test indirectly the batch job config file by validating with the Pydantic class model."
    job_name, config_path, env_names = inputs
    GoogleBatchJobConfig.init(
        job_name=job_name,
        config_path=config_path,
        env_names=env_names,
    )


def test_batch_extraction():
    """Test extraction of a batch of data from the dataset depending on the job type."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = os.path.join(tmp_dir, "data.parquet")
        extract_from_dataset(
            output_file_path=file_path,
            query_file_path=SPELLCHECK_QUERY_FILE_PATH,
            dataset_path=DIR / "data/dataset_sample.jsonl.gz",
        )
