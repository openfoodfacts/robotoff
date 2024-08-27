import pandas as pd
from google.cloud import storage


class GoogleStorageBucket:

    @staticmethod
    def download_gcs(bucket_name: str, suffix: str) -> pd.DataFrame:
        """Download parquet file from Google Storage Bucket.

        :param bucket_name: Bucket name
        :type bucket_name: str
        :param suffix: Path inside the bucket
        :type suffix: str
        :return: 
        :rtype: Any
        """
        client = storage.Client()
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(suffix)
        with blob.open("rb") as f:
            return pd.read_parquet(f)


    @staticmethod
    def upload_gcs(file_path: str, bucket_name: str, suffix: str) -> None:
        """Upload file to Google Storage Bucket.

        :param file_path: File path.
        :type file_path: str
        :param bucket_name: Bucket name.
        :type bucket_name: str
        :param suffix: Path inside the bucket.
        :type suffix: str
        """
        client = storage.Client()
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(suffix)
        blob.upload_from_filename(filename=file_path)
