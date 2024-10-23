import json
import os
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import Mock

import pytest

from robotoff.products import (
    convert_jsonl_to_parquet,
    is_special_image,
    is_valid_image,
)
from robotoff.settings import TEST_DATA_DIR
from robotoff.types import JSONType

with (TEST_DATA_DIR / "images.json").open("r") as f:
    IMAGE_DATA = json.load(f)


@pytest.mark.parametrize(
    "images,image_path,image_type,lang,output",
    [
        (IMAGE_DATA, "/303/371/006/5066/39.jpg", "nutrition", None, True),
        (IMAGE_DATA, "/303/371/006/5066/39.jpg", "nutrition", "fr", True),
        (IMAGE_DATA, "/303/371/006/5066/39.jpg", "nutrition", "de", False),
        (IMAGE_DATA, "/303/371/006/5066/1.jpg", "nutrition", None, False),
        (IMAGE_DATA, "/303/371/006/5066/1.jpg", "nutrition", "fr", False),
        (IMAGE_DATA, "/303/371/006/5066/6.jpg", "ingredients", None, True),
        (IMAGE_DATA, "/303/371/006/5066/6.jpg", "ingredients", "fr", False),
        (IMAGE_DATA, "/303/371/006/5066/34.jpg", "ingredients", "fr", True),
    ],
)
def test_is_special_image(
    images: JSONType,
    image_path: str,
    image_type: str,
    lang: Optional[str],
    output: bool,
):
    assert is_special_image(images, image_path, image_type, lang) is output


@pytest.mark.parametrize(
    "images,image_path,output",
    [
        (IMAGE_DATA, "/303/371/006/5066/39.jpg", True),
        (IMAGE_DATA, "/303/371/006/5066/1.jpg", True),
        (IMAGE_DATA, "/303/371/006/5066/6.jpg", True),
        (IMAGE_DATA, "/303/371/006/5066/34.jpg", True),
        (IMAGE_DATA, "/303/371/006/5066/azgzg.jpg", False),
        (IMAGE_DATA, "/303/371/006/5066/nutri_plus.jpg", False),
    ],
)
def test_is_valid_image(
    images: JSONType,
    image_path: str,
    output: bool,
):
    assert is_valid_image(images, image_path) is output


class TestConvertJSONLToParquet:
    def test_convert_jsonl_to_parquet(self, mocker: Mock):
        """This function doesn't test the DuckDB Query but only the logic of the `convert_jsonl_to_parquet`function.
        The reason is that the JSONL dataset schema can change over time, potentially leading to this test to fail.
        The JSONL schema validity responsability should remain out of this unittest.
        """
        # Mock the DuckDB SQL query and parquet writing
        mock_duckdb_sql = mocker.patch("duckdb.sql")
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file_path = os.path.join(tmp_dir, "test_converted.parquet")
            convert_jsonl_to_parquet(output_file_path=output_file_path)
        mock_duckdb_sql.assert_called_once()

    def test_convert_jsonl_to_parquet_data_missing(self):
        non_existing_path = Path("non/existing/dataset/path")
        with pytest.raises(FileNotFoundError):
            convert_jsonl_to_parquet(
                output_file_path="any_path",
                dataset_path=non_existing_path,
                query_path=non_existing_path,
            )
