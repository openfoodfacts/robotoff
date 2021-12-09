import json
import pathlib
from typing import Set

import dacite

from robotoff import settings
from robotoff.taxonomy import Taxonomy
from robotoff.utils import text_file_iter

from .dataclass import Config

PRODUCT_NAME_VOC_NAME = "product_name_voc.json"
CONFIG_NAME = "config.json"
CATEGORY_VOC_NAME = "category_voc.json"
CATEGORY_TAXONOMY_NAME = "category_taxonomy.json"
INGREDIENT_VOC_NAME = "ingredient_voc.json"


def load_product_name_vocabulary(model_dir: pathlib.Path):
    return load_json(model_dir / PRODUCT_NAME_VOC_NAME)


def load_category_vocabulary(model_dir: pathlib.Path):
    return load_json(model_dir / CATEGORY_VOC_NAME)


def load_ingredient_vocabulary(model_dir: pathlib.Path):
    return load_json(model_dir / INGREDIENT_VOC_NAME)


def load_config(model_dir: pathlib.Path) -> Config:
    config = load_json(model_dir / CONFIG_NAME)
    return dacite.from_dict(Config, config)


def load_taxonomy(model_dir: pathlib.Path) -> Taxonomy:
    return Taxonomy.from_json(model_dir / CATEGORY_TAXONOMY_NAME)


def load_json(path: pathlib.Path):
    with path.open("r") as f:
        return json.load(f)


def load_category_blacklist() -> Set[str]:
    return set(text_file_iter(settings.CATEGORY_CLF_CATEGORY_BLACKLIST))
