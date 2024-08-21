import pytest

from robotoff.batch import (
    GoogleBatchJobConfig,
    BatchJobType,
)

# Add future job types here for testing.
@pytest.mark.parametrize(
    "job_type_str",
    [
        "ingredients_spellcheck",
    ],
)
def test_batch_job_config_file(job_type_str):
    "Test indirectly the batch job config file by validating with the Pydantic class model."
    job_type = BatchJobType[job_type_str]
    GoogleBatchJobConfig.init(job_type)
