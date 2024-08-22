import pytest
import tempfile
from pathlib import Path

from robotoff.batch import (
    GoogleBatchJobConfig,
    BatchJobType,
    BatchExtraction,
)


DIR = Path(__file__).parent
JOB_TYPES = [
    "ingredients_spellcheck",
]


# Add future job types here for testing.
@pytest.mark.parametrize(
    "job_type_str",
    JOB_TYPES,
)
def test_batch_job_config_file(job_type_str):
    "Test indirectly the batch job config file by validating with the Pydantic class model."
    job_type = BatchJobType[job_type_str]
    GoogleBatchJobConfig.init(job_type)


# Add future job types here for testing.
@pytest.mark.parametrize(
    "job_type_str",
    JOB_TYPES,
)
def test_batch_extraction(job_type_str):
    """Test extraction of a batch of data from the dataset depending on the job type.
    """
    job_type_str = BatchJobType[job_type_str]
    with tempfile.TemporaryDirectory() as tmp_dir:
        BatchExtraction.extract_from_dataset(
            job_type=job_type_str,
            output_dir=tmp_dir,
            dataset_path=str(DIR / "data/dataset_sample.jsonl.gz"),
        )
