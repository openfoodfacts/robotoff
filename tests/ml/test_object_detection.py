import typing
from pathlib import Path

import numpy as np
import pytest
import requests

from robotoff.images import get_image_from_url
from robotoff.prediction.object_detection.core import MODELS_CONFIG, RemoteModel
from robotoff.types import ObjectDetectionModel
from robotoff.utils import dump_json
from robotoff.utils.download import get_asset_from_url


@pytest.mark.parametrize(
    "model_enum, image_url, expected_result_url",
    [
        # Nutriscore model
        (
            # Nutriscore A
            ObjectDetectionModel.nutriscore,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/0000020047238_122.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/0000020047238_122.json",
        ),
        (
            # Nutriscore B
            ObjectDetectionModel.nutriscore,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/3229820769165_43.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/3229820769165_43.json",
        ),
        (
            # Nutriscore C
            ObjectDetectionModel.nutriscore,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/3033710084913_67.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/3033710084913_67.json",
        ),
        (
            # Nutriscore D
            ObjectDetectionModel.nutriscore,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/0000020713713_35.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/0000020713713_35.json",
        ),
        (
            # Nutriscore E
            ObjectDetectionModel.nutriscore,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/3023470001015_103.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/3023470001015_103.json",
        ),
        (
            # No Nutriscore
            ObjectDetectionModel.nutriscore,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/3023470001015_92.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/c9187c1fe0dc6b5117f3828200f133846382dffa/robotoff/tests/ml/object_detection/nutriscore/3023470001015_92.json",
        ),
        # Nutrition table model
        (
            ObjectDetectionModel.nutrition_table,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/15fd73bcc86649916eb313d08618f5c6f4b24eef/robotoff/tests/ml/object_detection/nutrition_table/20005733_117.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/15fd73bcc86649916eb313d08618f5c6f4b24eef/robotoff/tests/ml/object_detection/nutrition_table/20005733_117.json",
        ),
        (
            ObjectDetectionModel.nutrition_table,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/15fd73bcc86649916eb313d08618f5c6f4b24eef/robotoff/tests/ml/object_detection/nutrition_table/3596710368259_2.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/15fd73bcc86649916eb313d08618f5c6f4b24eef/robotoff/tests/ml/object_detection/nutrition_table/3596710368259_2.json",
        ),
        (
            ObjectDetectionModel.nutrition_table,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/15fd73bcc86649916eb313d08618f5c6f4b24eef/robotoff/tests/ml/object_detection/nutrition_table/3770007136121_1.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/15fd73bcc86649916eb313d08618f5c6f4b24eef/robotoff/tests/ml/object_detection/nutrition_table/3770007136121_1.json",
        ),
        (
            ObjectDetectionModel.nutrition_table,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/15fd73bcc86649916eb313d08618f5c6f4b24eef/robotoff/tests/ml/object_detection/nutrition_table/4908837321137_1.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/15fd73bcc86649916eb313d08618f5c6f4b24eef/robotoff/tests/ml/object_detection/nutrition_table/4908837321137_1.json",
        ),
        # Universal logo detector model
        (
            ObjectDetectionModel.universal_logo_detector,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/626e9cc8e482f4d0ed227af8d7e40794acd0a347/robotoff/tests/ml/object_detection/universal_logo_detector/0074306802576_1.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/626e9cc8e482f4d0ed227af8d7e40794acd0a347/robotoff/tests/ml/object_detection/universal_logo_detector/0074306802576_1.json",
        ),
        (
            ObjectDetectionModel.universal_logo_detector,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/626e9cc8e482f4d0ed227af8d7e40794acd0a347/robotoff/tests/ml/object_detection/universal_logo_detector/3585510025677_9.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/626e9cc8e482f4d0ed227af8d7e40794acd0a347/robotoff/tests/ml/object_detection/universal_logo_detector/3585510025677_9.json",
        ),
        (
            ObjectDetectionModel.universal_logo_detector,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/626e9cc8e482f4d0ed227af8d7e40794acd0a347/robotoff/tests/ml/object_detection/universal_logo_detector/7640104959519_10.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/626e9cc8e482f4d0ed227af8d7e40794acd0a347/robotoff/tests/ml/object_detection/universal_logo_detector/7640104959519_10.json",
        ),
        # Price tag detection
        (
            ObjectDetectionModel.price_tag_detection,
            "https://prices.openfoodfacts.org/img/0098/BrhJfXQjGl.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/6b0610962b64ef838a0666a1761dad2236fb1bc8/robotoff/tests/ml/object_detection/price_tag_detection/0098_BrhJfXQjGl.json",
        ),
        (
            ObjectDetectionModel.price_tag_detection,
            "https://prices.openfoodfacts.org/img/0098/Zk8V8WapT6.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/6b0610962b64ef838a0666a1761dad2236fb1bc8/robotoff/tests/ml/object_detection/price_tag_detection/0098_Zk8V8WapT6.json",
        ),
        (
            ObjectDetectionModel.price_tag_detection,
            "https://prices.openfoodfacts.org/img/0097/WUHi0c9Qqf.webp",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/6b0610962b64ef838a0666a1761dad2236fb1bc8/robotoff/tests/ml/object_detection/price_tag_detection/0097_WUHi0c9Qqf.json",
        ),
    ],
)
def test_detect_from_image(
    model_enum: ObjectDetectionModel,
    image_url: str,
    expected_result_url: str,
    triton_uri: str,
    update_results: bool,
    output_dir: Path,
):
    """Test the RemoteModel.detect_from_image method.

    To update the results without running the test, use the following command:
    ```shell
    pytest tests/ml/test_object_detection.py --update-results --output-dir data
    ```

    To check against a different Triton server, use the following command:
    ```shell
    pytest tests/ml/test_object_detection.py --triton-uri <URI>
    ```
    """
    image = typing.cast(
        np.ndarray, get_image_from_url(image_url, error_raise=True, return_type="np")
    )
    result = RemoteModel(MODELS_CONFIG[model_enum]).detect_from_image(
        image, triton_uri=triton_uri
    )
    result_list = result.to_list()
    for prediction in result_list:
        prediction["bounding_box"] = list(prediction["bounding_box"])

    is_output_available = requests.head(expected_result_url).status_code == 200

    if update_results:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / expected_result_url.split("/")[-1]
        dump_json(output_path, result_list, compressed=False)
    elif is_output_available:
        r = get_asset_from_url(expected_result_url)
        assert r is not None
        expected = r.json()
        assert len(result_list) == len(expected)
        for i, item in enumerate(expected):
            current_prediction = result_list[i]
            assert set(current_prediction.keys()) == set(item.keys())
            assert current_prediction["label"] == item["label"]
            assert item["score"] == pytest.approx(current_prediction["score"], rel=1e-3)
            assert item["bounding_box"] == pytest.approx(
                current_prediction["bounding_box"], rel=1e-3
            )

    else:
        raise RuntimeError("Output not available and update_results is False")
