import os
import pathlib

PROJECT_DIR = pathlib.Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"

SENTRY_DSN = os.environ.get("SENTRY_DSN")
INDEX_DIM = 1280

INDEX_FILE_NAME = "index.bin"
KEYS_FILE_NAME = "index.txt"

DEFAULT_INDEX = "efficientnet-b0"
