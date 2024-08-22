import io

from robotoff.utils.buckets import GoogleStorageBucket
from robotoff.batch import BatchJobType


BATCH_JOB_TYPE_TO_BUCKET = {
    BatchJobType.ingredients_spellcheck: {
        "bucket": "robotoff-spellcheck", 
        "suffix_preprocess": "data/preprocessed_data.parquet",
        "suffix_postprocess": "data/postprocessed_data.parquet",
    },
}


class GoogleStorageBucketForBatchJob(GoogleStorageBucket):
    """Class to handle the Google Storage bucket for depending on the batch job.

    :param bucket: Bucket name
    :type bucket: str
    :param suffix_preprocess: Path inside the bucket before batch processing.
    :type suffix_preprocess: str
    :param suffix_postprocess: Path inside the bucket after batch processing.
    :type suffix_postprocess: str
    """

    def __init__(
        self,
        bucket: str,
        suffix_preprocess: str,
        suffix_postprocess: str,
    ) -> None:
        self.bucket = bucket
        self.suffix_preprocess = suffix_preprocess
        self.suffix_postprocess = suffix_postprocess
    
    @classmethod
    def from_job_type(cls, job_type:BatchJobType) -> "GoogleStorageBucketForBatchJob":
        """Initialize the class with the configuration file corresponding to the batch job type.
        Useful to adapt bucket upload and download during the batch job process.

        :param job_type: Batch job type. 
        :type job_type: BatchJobType
        :return: Instantiated class.
        :rtype: GoogleStorageBucketForBatchJob
        """
        try: 
            bucket_dict = BATCH_JOB_TYPE_TO_BUCKET[job_type]
        except KeyError:
            raise ValueError(f"Batch job type {job_type} not found in the configuration. Expected {BATCH_JOB_TYPE_TO_BUCKET}.")
        return cls(**bucket_dict)

    def upload_file(self, file_path: str):
        """Upload file to the bucket.

        :param file_path: File path to upload.
        :type file_path: str
        """
        self.upload_gcs(
            file_path=file_path,
            bucket_name=self.bucket,
            suffix=self.suffix_preprocess,
        )

    def download_file(self) -> io.BufferedReader:
        """Download file from bucket
        """
        return self.download_gcs(
            bucket_name=self.bucket,
            suffix=self.suffix_postprocess,
        )
