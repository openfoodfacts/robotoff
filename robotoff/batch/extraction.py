from pathlib import Path

import duckdb

from robotoff import settings
from robotoff.utils import get_logger

logger = get_logger(__name__)


def extract_from_dataset(
    query_file_path: Path,
    output_file_path: str,
    dataset_path: Path = settings.JSONL_DATASET_PATH,
) -> None:
    """Using SQL queries, extract data from the dataset and save it as a parquet file.

    :param query_file_path: Path to the SQL file relative to the job.
    :type query_file_path: Path
    :param output_file_path: Path to save the extracted data.
    :type output_file_path: str
    :param dataset_path: Compressed jsonl database, defaults to settings.JSONL_DATASET_PATH
    :type dataset_path: Path, optional
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path {str(dataset_path)} not found.")
    query = _load_query(query_file_path=query_file_path, dataset_path=dataset_path)
    _extract_and_save_batch_data(query=query, output_file_path=output_file_path)
    logger.debug(f"Batch data succesfully extracted and saved at {output_file_path}")


def _load_query(query_file_path: Path, dataset_path: Path) -> str:
    """Load the SQL query from a corresponding file.

    :param query_file_path: Path to the SQL file relative to the job.
    :type query_file_path: Path
    :param dataset_path: Path to the dataset.
    :type dataset_path: Path
    :return: SQL query.
    """
    query = query_file_path.read_text()
    if "DATASET_PATH" not in query:
        raise ValueError(
            "The SQL query should contain the string 'DATASET_PATH' to replace it with the dataset path."
        )
    query = query.replace("DATASET_PATH", str(dataset_path))
    logger.debug(f"Query used to extract batch from dataset: {query}")
    return query


def _extract_and_save_batch_data(query: str, output_file_path: str) -> None:
    """Query and save the data.

    :param query: SQL query.
    :type query: str
    :param output_file_path: Path to save the extracted data.
    :type output_file_path: str
    """
    (duckdb.sql(query).write_parquet(output_file_path))
