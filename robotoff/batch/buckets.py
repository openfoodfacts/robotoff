import pandas as pd
from google.cloud import storage


def upload_file_to_gcs(file_path: str, bucket_name: str, suffix: str) -> None:
    """Upload file to Google Storage Bucket.

    :param file_path: File where the data is stored
    :type file_path: str
    :param bucket_name: Bucket name in GCP storage
    :type bucket_name: str
    :param suffix: Path inside the bucket
    :type suffix: str
    """
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(suffix)
    blob.upload_from_filename(filename=file_path)


def fetch_dataframe_from_gcs(bucket_name: str, suffix: str) -> pd.DataFrame:
    """Download parquet file from Google Storage Bucket.


    :param bucket_name: Bucket name in GCP storage
    :type bucket_name: str
    :param suffix: Path inside the bucket. Should lead to a parquet file.
    :type suffix: str
    :return: Dataframe
    """
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(suffix)
    with blob.open("rb") as f:
        try: 
            df = pd.read_parquet(f)
        except Exception as e:
            raise ValueError(f"Could not read parquet file from {bucket_name}/{suffix}. Error: {e}")
        return df
