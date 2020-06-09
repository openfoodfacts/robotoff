import os
import pathlib
from typing import Dict

PROJECT_DIR = pathlib.Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"

SENTRY_DSN = os.environ.get("SENTRY_DSN")
INDEX_DIM: Dict[str, int] = {"efficientnet-b0": 1280, "efficientnet-b5": 2048}
IMAGE_INPUT_DIM: Dict[str, int] = {"efficientnet-b0": 224}

INDEX_FILE_NAME = "index.bin"
KEYS_FILE_NAME = "index.txt"

DEFAULT_INDEX = "efficientnet-b0"
DEFAULT_MODEL = "efficientnet-b0"
DEFAULT_HDF5_COUNT = 10000000
EMBEDDINGS_HDF5_PATH = DATA_DIR / "efficientnet-b0.hdf5"
