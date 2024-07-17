"""
Helper to download weights files for different Robotoff models.
"""
import shutil
from pathlib import Path

import requests

from robotoff.utils import get_logger

logger = get_logger(__name__)


def download_file(url: str, destination: Path, force: bool = False) -> None:
    """
    Efficiently download a file from an URL.

    Taken from https://stackoverflow.com/a/39217788.
    """
    # Check if file exists
    if destination.is_file():
        logger.info("Destination file already exists: %s", destination)

        if not force:
            logger.info("Skip download from %s", url)
            return
        else:
            logger.info("--force used")

    # Create directory if needed
    file_dir = destination.parent
    if not file_dir.is_dir():
        logger.info("Create directory: %s", file_dir)
        file_dir.mkdir(exist_ok=True, parents=True)

    # Download file
    logger.info("Start download from %s to %s.", url, destination)
    with requests.get(url, stream=True) as r:
        with destination.open("wb") as f:
            shutil.copyfileobj(r.raw, f)  # type: ignore
    logger.info("Download complete.")
