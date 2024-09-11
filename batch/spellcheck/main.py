import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import List

import pandas as pd
import requests
from google.cloud import storage
from vllm import LLM, SamplingParams

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

FEATURES_VALIDATION = ["code", "text"]


def parse() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Spellcheck module.")
    parser.add_argument(
        "--model_path",
        default="openfoodfacts/spellcheck-mistral-7b",
        type=str,
        help="HF model path.",
    )
    parser.add_argument(
        "--max_model_len",
        default=1024,
        type=int,
        help="Maximum model context length. A lower max context length reduces the memory footprint and accelerate the inference.",
    )
    parser.add_argument(
        "--temperature", default=0, type=float, help="Sampling temperature."
    )
    parser.add_argument(
        "--max_tokens",
        default=1024,
        type=int,
        help="Maximum number of tokens to generate.",
    )
    parser.add_argument(
        "--quantization", default="fp8", type=str, help="Quantization type."
    )
    parser.add_argument(
        "--dtype",
        default="auto",
        type=str,
        help="Model weights precision. Default corresponds to the modle config (float16 here)",
    )
    return parser.parse_args()


def main():
    """Batch processing job.

    Original lists of ingredients are stored in a gs bucket before being loaded then
    processed by the model. The corrected lists of ingredients are then stored back in
    gs.

    We use vLLM to process the batch optimaly. The model is loaded from the Open Food
    Facts Hugging Face model repository.
    """
    logger.info("Starting batch processing job.")
    args = parse()

    bucket_name = os.environ["BUCKET_NAME"]
    input_file_path = os.environ["INPUT_FILE_PATH"]
    output_file_path = os.environ["OUTPUT_FILE_PATH"]
    logger.info(
        "Loading data from GCS: %s/%s",
        bucket_name,
        input_file_path,
    )
    data = load_gcs(bucket_name=bucket_name, suffix=input_file_path)
    logger.info(f"Feature in uploaded data: {data.columns}")
    if not all(feature in data.columns for feature in FEATURES_VALIDATION):
        raise ValueError(
            f"Data should contain the following features: {FEATURES_VALIDATION}. Current features: {data.columns}"
        )

    instructions = [prepare_instruction(text) for text in data["text"]]
    llm = LLM(
        model=args.model_path,
        max_model_len=args.max_model_len,
        dtype=args.dtype,
        quantization=args.quantization,
    )
    sampling_params = SamplingParams(
        temperature=args.temperature, max_tokens=args.max_tokens
    )

    logger.info(f"Starting batch inference, sampling parameters: {sampling_params}")
    data["correction"] = batch_inference(
        instructions, llm=llm, sampling_params=sampling_params
    )

    logger.info("Uploading data to GCS: %s/%s", bucket_name, output_file_path)
    # Save DataFrame as Parquet to a temporary file
    with tempfile.NamedTemporaryFile(delete=True, suffix=".parquet") as temp_file:
        data.to_parquet(temp_file.name)
        temp_file_name = temp_file.name
        upload_gcs(temp_file_name, bucket_name=bucket_name, suffix=output_file_path)

    batch_dir = str(Path(output_file_path).parent)
    logger.info(
        "Request Robotoff API batch import endpoint with batch_dir: %s", batch_dir
    )
    run_robotoff_endpoint_batch_import(batch_dir)

    logger.info("Batch processing job completed.")


def prepare_instruction(text: str) -> str:
    """Prepare instruction prompt for fine-tuning and inference.

    Args:
        text (str): List of ingredients

    Returns:
        str: Instruction.
    """
    instruction = (
        "###Correct the list of ingredients:\n" + text + "\n\n###Correction:\n"
    )
    return instruction


def batch_inference(
    texts: List[str], llm: LLM, sampling_params: SamplingParams
) -> List[str]:
    """Process batch of texts with vLLM.

    Args:
        texts (List[str]): Batch
        llm (LLM): Model engine optimized with vLLM
        sampling_params (SamplingParams): Generation parameters

    Returns:
        List[str]: Processed batch of texts
    """
    outputs = llm.generate(
        texts,
        sampling_params,
    )
    corrections = [output.outputs[0].text for output in outputs]
    return corrections


def load_gcs(bucket_name: str, suffix: str) -> pd.DataFrame:
    """Load data from Google Cloud Storage bucket.

    Args:
        bucket_name (str):
        suffix (str): Path inside the bucket

    Returns:
        pd.DataFrame: Df from parquet file.
    """
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(suffix)
    with blob.open("rb") as f:
        df = pd.read_parquet(f)
    return df


def upload_gcs(file_path: str, bucket_name: str, suffix: str) -> None:
    """Upload data to GCS.

    Args:
        filepath (str): File path to export.
        bucket_name (str): Bucket name.
        suffix (str): Path inside the bucket.
    """
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(suffix)
    blob.upload_from_filename(filename=file_path)


def run_robotoff_endpoint_batch_import(batch_dir: str):
    """Run Robotoff api endpoint to import batch data into tables."""
    if "WEBHOOK_URL" not in os.environ or "BATCH_JOB_KEY" not in os.environ:
        logger.error(
            "WEBHOOK_URL and/or BATCH_JOB_KEY environment variable is missing."
        )
        return

    url = os.environ["WEBHOOK_URL"]
    data = {"job_type": "ingredients_spellcheck", "batch_dir": batch_dir}
    headers = {
        "Authorization": f"Bearer {os.environ['BATCH_JOB_KEY']}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            url,
            data=data,
            headers=headers,
        )
        logger.info(
            f"Import batch Robotoff API endpoint succesfully requested: {response.text}"
        )
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


if __name__ == "__main__":
    main()
