import os
import tempfile
from pathlib import Path

import duckdb
import pytest

from robotoff import settings
from robotoff.batch import GoogleBatchJobConfig, extract_from_dataset
from tests.unit.pytest_utils import get_asset

DIR = Path(__file__).parent
SPELLCHECK_BATCH_JOB_CONFIG_PATH = (
    settings.BATCH_JOB_CONFIG_DIR / "job_configs/spellcheck.yaml"
)


@pytest.mark.parametrize(
    "job_name,config_path,env_variables",
    [
        ("ingredients-spellcheck", SPELLCHECK_BATCH_JOB_CONFIG_PATH, {"KEY": "value"}),
    ],
)
def test_batch_job_config_file(job_name, config_path, env_variables):
    """Test indirectly the batch job config file by validating with the Pydantic class
    model."""
    GoogleBatchJobConfig.init(
        job_name=job_name,
        config_path=config_path,
        env_variables=env_variables,
    )


def test_batch_extraction():
    """Test extraction of a batch of data from the dataset depending on the job type."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = os.path.join(tmp_dir, "data.parquet")
        dataset_path = Path(tmp_dir) / "food_sample.parquet"
        dataset_path.write_bytes(get_asset("/robotoff/tests/unit/food_sample.parquet"))
        extract_from_dataset(
            output_file_path=file_path,
            dataset_path=dataset_path,
            limit=100,
        )
        items = duckdb.query(f"SELECT * FROM '{file_path}'").fetchall()
        assert len(items) == 100

        first_item = items[0]
        assert first_item == (
            "0022314010025",
            "Châtaignes (50%), sucre, marrons glacés (châtaignes (54,6%), sucre, sirop de glucose, extrait de vanille Madagascar), extrait de vanille Madagascar.",
            "fr",
            0.375,
        )
