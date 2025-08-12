import typing
from pathlib import Path

import pytest
import requests
from PIL import Image

from robotoff.images import get_image_from_url
from robotoff.prediction.image_classifier import LABEL_NAMES, ImageClassifier
from robotoff.types import ImageClassificationModel
from robotoff.utils import dump_json
from robotoff.utils.download import get_asset_from_url


@pytest.mark.parametrize(
    "model_enum, image_url, expected_result_url",
    [
        # Price proof classification
        (
            # Receipt
            ImageClassificationModel.price_proof_classification,
            "https://raw.githubusercontent.com/openfoodfacts/test-data/2646fe4ceec8b3356ef2a9d46891e8a143959ed2/robotoff/tests/ml/image_classification/price_proof_classification/0100_42xrafPHyY.webp",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/2646fe4ceec8b3356ef2a9d46891e8a143959ed2/robotoff/tests/ml/image_classification/price_proof_classification/0100_42xrafPHyY.json",
        ),
        (
            # Shelf
            ImageClassificationModel.price_proof_classification,
            "https://prices.openfoodfacts.org/img/0100/8ZVgD29AhM.webp",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/2646fe4ceec8b3356ef2a9d46891e8a143959ed2/robotoff/tests/ml/image_classification/price_proof_classification/0100_8ZVgD29AhM.json",
        ),
        (
            # Price tag
            ImageClassificationModel.price_proof_classification,
            "https://prices.openfoodfacts.org/img/0100/ithb89lJBe.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/2646fe4ceec8b3356ef2a9d46891e8a143959ed2/robotoff/tests/ml/image_classification/price_proof_classification/0100_ithb89lJBe.json",
        ),
    ],
)
def test_detect_from_image(
    model_enum: ImageClassificationModel,
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
    image = typing.cast(Image.Image, get_image_from_url(image_url, error_raise=True))
    results_tuples = ImageClassifier(model_enum.name, LABEL_NAMES[model_enum]).predict(
        image, triton_uri=triton_uri
    )
    results = [list(x) for x in results_tuples]

    is_output_available = requests.head(expected_result_url).status_code == 200

    if update_results:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / expected_result_url.split("/")[-1]
        dump_json(output_path, results, compressed=False)
    elif is_output_available:
        r = get_asset_from_url(expected_result_url)
        assert r is not None
        expected = r.json()
        assert len(results) == len(expected)
        for predicted_result, expected_result in zip(results, expected):
            assert predicted_result[0] == expected_result[0]
            assert predicted_result[1] == pytest.approx(expected_result[1], rel=1e-3)
    else:
        raise RuntimeError("Output not available and update_results is False")
