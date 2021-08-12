import os
import pathlib
from typing import Dict, Sequence

import sentry_sdk
from sentry_sdk.integrations import Integration

PROJECT_DIR = pathlib.Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"

INDEX_DIM: Dict[str, int] = {"efficientnet-b0": 1280, "efficientnet-b5": 2048}
IMAGE_INPUT_DIM: Dict[str, int] = {"efficientnet-b0": 224}

INDEX_FILE_NAME = "index.bin"
KEYS_FILE_NAME = "index.txt"

DEFAULT_INDEX = "efficientnet-b0"
DEFAULT_MODEL = "efficientnet-b0"
DEFAULT_HDF5_COUNT = 10000000
EMBEDDINGS_HDF5_PATH = DATA_DIR / "efficientnet-b0.hdf5"

# Should be either 'prod' or 'dev'.
_ann_instance = os.environ.get("ANN_INSTANCE", "prod")

if _ann_instance != "prod" and _ann_instance != "dev":
    raise ValueError(
        "ANN_INSTANCE should be either 'prod' or 'dev', got %s" % _ann_instance
    )

_sentry_dsn = os.environ.get("SENTRY_DSN")


def init_sentry(integrations: Sequence[Integration] = ()):
    if _sentry_dsn:
        sentry_sdk.init(
            _sentry_dsn,
            environment=_ann_instance,
            integrations=integrations,
        )
    else:
        raise ValueError(
            "init_sentry was requested, yet SENTRY_DSN env variable was not provided"
        )
