import os
from pathlib import Path

import duckdb

from robotoff import settings
from robotoff.batch import BatchJobType


BATCH_JOB_TYPE_TO_QUERY_FILE_PATH = {
    BatchJobType.ingredients_spellcheck: settings.BATCH_JOB_CONFIG_DIR / "sql/spellcheck.sql",
}


class BatchExtraction:
    """Handle batch extraction from the dataset.
    Extraction varies regarding the batch job.
    """

    file_name: str = "batch.parquet"
    extracted_file_path: str = None

    @classmethod
    def extract_from_dataset(
        cls, 
        job_type: BatchJobType,
        output_dir: str, 
        dataset_path: str = str(settings.JSONL_DATASET_PATH), 
    ) -> None:
        """Using SQL queries, extract data from the dataset and save it as a parquet file.

        :param job_type: Batch job type.
        :type job_type: BatchJobType
        :param output_dir: Directory to save the extracted data as a parquet file.
        :type output_dir: str
        :param dataset_path: Path to the jsonl.gz dataset.
        :type dataset_path: Path, optional. Default to settings.JSONL_DATASET_PATH. Mainly used for testing.
        """
        if not isinstance(dataset_path, str):
            raise ValueError(f"The dataset path should be a string. Current type {type(dataset_path)}")
        
        query_file_path = BATCH_JOB_TYPE_TO_QUERY_FILE_PATH[job_type]
        query = cls._load_query(query_file_path=query_file_path, dataset_path=dataset_path)
        cls._extract_and_save_batch_data(query=query, output_dir=output_dir)
        # We save the file path for later usage in the pipeline
        cls.extracted_file_path = os.path.join(output_dir, cls.file_name)

    @staticmethod
    def _load_query(query_file_path: Path, dataset_path: str) -> str:
        """Load the SQL query from a corresponding file.

        :param query_file_path: File path containing the SQL query.
        :type query_file_path: Path
        :param dataset_path: Path to the jsonl.gz dataset.
        :type dataset_path: Path   
        :raises ValueError: In case the Dataset path is not found in the SQL query.
        :return: the SQL/DuckDB query.
        :rtype: str
        """
        query = query_file_path.read_text()
        if "DATASET_PATH" not in query:
            raise ValueError(
                "The SQL query should contain the string 'DATASET_PATH' to replace it with the dataset path."
            )
        query = query.replace("DATASET_PATH", dataset_path)
        return query

    @classmethod
    def _extract_and_save_batch_data(cls, query: str, output_dir: str) -> None:
        """Query and save the data.

        :param query: DuckDB/SQL query.
        :type query: str
        :param output_dir: Extracted data directory
        :type output_dir: str
        """
        (
            duckdb
            .sql(query)
            .write_parquet(os.path.join(output_dir, cls.file_name))
        )
