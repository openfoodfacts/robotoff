import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import duckdb
import pandas as pd
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


@patch("robotoff.batch.predict_lang")
@patch("robotoff.batch.fetch_dataframe_from_gcs")
@patch("robotoff.batch.import_insights")
@patch("robotoff.batch.check_google_credentials")
def test_spellcheck_html_entity_decoding(
    _mock_check_creds, mock_import_insights, mock_fetch_df, mock_predict_lang
):
    """Test HTML entities (e.g. &quot;) are decoded in spellcheck predictions."""
    from robotoff.batch import import_spellcheck_batch_predictions
    from robotoff.prediction.langid import LanguagePrediction

    mock_df = pd.DataFrame(
        {
            "code": ["4025500283148"],
            "text": [
                "Buttermilch, Zucker, Wasser, 3% Heidelbeersaft&quot; aus Heidelbeersaftkonzentrat"
            ],
            "correction": [
                'Buttermilch, Zucker, Wasser, 3% Heidelbeersaft" aus Heidelbeersaftkonzentrat'
            ],
            "lang": ["de"],
        }
    )
    mock_fetch_df.return_value = mock_df
    mock_predict_lang.return_value = [LanguagePrediction(lang="de", confidence=0.99)]

    import_spellcheck_batch_predictions("test_batch_dir")

    assert mock_import_insights.called
    call_args = mock_import_insights.call_args
    predictions = call_args[1]["predictions"]

    assert len(predictions) == 1
    prediction = predictions[0]

    assert "&quot;" not in prediction.data["original"]
    assert '"' in prediction.data["original"]
    assert (
        prediction.data["original"]
        == 'Buttermilch, Zucker, Wasser, 3% Heidelbeersaft" aus Heidelbeersaftkonzentrat'
    )
    assert (
        prediction.data["correction"]
        == 'Buttermilch, Zucker, Wasser, 3% Heidelbeersaft" aus Heidelbeersaftkonzentrat'
    )
