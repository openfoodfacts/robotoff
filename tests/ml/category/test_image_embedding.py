import io
from pathlib import Path

import numpy as np
import pytest
import requests

from robotoff.images import get_image_from_url
from robotoff.prediction.category.neural.keras_category_classifier_3_0 import (
    _generate_image_embeddings,
)
from robotoff.triton import GRPCInferenceServiceStub
from robotoff.utils.download import get_asset_from_url


@pytest.mark.parametrize(
    "image_urls",
    [
        [
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/4056489895008_1.400.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/4056489895008_2.400.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/8414192311936_15.40.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/4099100116205_4.400.jpg",
            # Add a few raw images as well
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/9001375996494_1.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/5400141167801_3.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/3256220787321_1.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/3256220787321_2.jpg",
            "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/6420488009731_1.jpg",
        ]
    ],
)
def test__generate_image_embeddings(
    image_urls: list[str],
    triton_stub: GRPCInferenceServiceStub,
    update_results: bool,
    output_dir: Path,
):
    """Test the _generate_image_embeddings function.

    To update the results without running the test, use the following command:
    ```shell
    pytest tests/ml/category/test_image_embedding.py --update-results
    ```

    To check against a different Triton server, use the following command:
    ```shell
    pytest tests/ml/category/test_image_embedding.py --triton-uri <URI>
    ```
    """
    images_by_id = {}
    for image_url in image_urls:
        image = get_image_from_url(image_url)
        if image:
            images_by_id[image_url.split("/")[-1]] = image

    embeddings = _generate_image_embeddings(images_by_id, triton_stub)
    output_url = "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/ml/category/image_embeddings/test_image_embedding.npz"
    is_output_available = requests.head(output_url).status_code == 200

    if update_results:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_url.split("/")[-1]
        np.savez(output_path, **embeddings)
    elif is_output_available:
        r = get_asset_from_url(output_url)
        assert r is not None
        f = io.BytesIO(r.content)
        expected = np.load(f)
        assert set(images_by_id) == set(expected)
        for image_url in images_by_id:
            expected_embedding = expected[image_url]
            embedding = embeddings[image_url]
            # compute cosine similarity and check that it's close to 1
            assert (
                np.dot(expected_embedding, embedding)
                / (np.linalg.norm(expected_embedding) * np.linalg.norm(embedding))
                > 0.99
            )
    else:
        raise RuntimeError("Output not available and update_results is False")
