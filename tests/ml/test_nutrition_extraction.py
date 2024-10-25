import dataclasses
import io
import json
import pickle
from pathlib import Path
from typing import cast

import pytest
import requests
from openfoodfacts import OCRResult
from openfoodfacts.images import download_image
from PIL import Image

from robotoff.prediction.nutrition_extraction import (
    MODEL_DIR,
    get_processor,
    predict,
    preprocess,
)
from robotoff.utils.download import get_asset_from_url


@pytest.mark.parametrize(
    "image_url",
    [
        "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/nutrition_extraction/0011110702081_2.jpg",
        "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/nutrition_extraction/2509757363133_2.jpg",
        "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/nutrition_extraction/4903015130266_2.jpg",
    ],
)
def test_preprocess(image_url: str, output_dir: Path, update_results: bool):
    processor = get_processor(MODEL_DIR)
    image = cast(Image.Image, download_image(image_url))
    output_url = image_url.replace(".jpg", ".pkl").replace(
        "nutrition_extraction/", "nutrition_extraction/preprocess_"
    )
    ocr_result = cast(OCRResult, OCRResult.from_url(image_url.replace(".jpg", ".json")))
    result = preprocess(image, ocr_result, processor)
    assert result is not None
    words, char_offsets, bboxes, batch_encoding = result

    is_output_available = requests.head(output_url).status_code == 200

    if is_output_available:
        r = get_asset_from_url(output_url)
        assert r is not None
        f = io.BytesIO(r.content)
        expected = pickle.load(f)
        assert len(expected) == len(result)
        assert expected[0] == words
        assert expected[1] == char_offsets
        assert expected[2] == bboxes

        # batch_encoding
        for key, value in expected[3].items():
            assert (batch_encoding[key] == value).all()

    elif update_results:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = output_url.split("/")[-1]
        with (output_dir / output_filename).open("wb") as g:
            pickle.dump((words, char_offsets, bboxes, batch_encoding), g)

    else:
        raise RuntimeError("Output not available and update_results is False")


@pytest.mark.parametrize(
    "image_url",
    [
        "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/nutrition_extraction/0011110702081_2.jpg",
        "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/nutrition_extraction/2509757363133_2.jpg",
        "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/nutrition_extraction/4903015130266_2.jpg",
    ],
)
def test_predict(
    image_url: str, output_dir: Path, update_results: bool, triton_uri: str
):
    image = cast(Image.Image, download_image(image_url))
    output_url = image_url.replace(".jpg", ".json").replace(
        "nutrition_extraction/", "nutrition_extraction/predict_"
    )
    ocr_result = cast(OCRResult, OCRResult.from_url(image_url.replace(".jpg", ".json")))
    result = predict(image, ocr_result, triton_uri=triton_uri)
    assert result is not None

    is_output_available = requests.head(output_url).status_code == 200

    if update_results:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = output_url.split("/")[-1]

        with (output_dir / output_filename).open("wt") as f:
            json.dump(dataclasses.asdict(result), f, indent=4)
    elif is_output_available:
        r = get_asset_from_url(output_url)
        assert r is not None
        g = io.BytesIO(r.content)
        expected = json.load(g)
        assert expected == dataclasses.asdict(result)
    else:
        raise RuntimeError("Output not available and update_results is False")
