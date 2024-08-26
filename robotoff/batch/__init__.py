import tempfile

from .launch import (
    GoogleBatchJob,
    GoogleBatchJobConfig,
    BatchJobType,
)
from .extraction import (
    BatchExtraction,
)
from .buckets import (
    GoogleStorageBucketForBatchJob,
)
from .importer import generate_predictions_from_batch

from robotoff.utils import get_logger


LOGGER = get_logger(__name__)


def launch_batch_job(job_type: BatchJobType) -> None:
    """_summary_

    :param job_type: _description_
    :type job_type: BatchJobType
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        BatchExtraction.extract_from_dataset(
            job_type=job_type,
            output_dir=tmp_dir,
        )
        if not BatchExtraction.extracted_file_path:
            raise ValueError("The extracted file was not found.")
        LOGGER.debug(f"Batch data succesfully extracted and saved at {BatchExtraction.extracted_file_path}")

        # Upload the extracted file to the bucket
        bucket_handler = GoogleStorageBucketForBatchJob.from_job_type(job_type)
        bucket_handler.upload_file(file_path=BatchExtraction.extracted_file_path)
        LOGGER.debug(f"File uploaded to the bucket {bucket_handler.bucket}")

    # Launch batch job
    batch_job_config = GoogleBatchJobConfig.init(job_type=job_type)
    batch_job = GoogleBatchJob.launch_job(batch_job_config=batch_job_config)
    LOGGER.info(f"Batch job succesfully launched. Batch job name: {batch_job.name}")
