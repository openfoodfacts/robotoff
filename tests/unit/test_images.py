from pathlib import Path

from openfoodfacts.images import download_image
from PIL import Image

from robotoff.images import generate_image_fingerprint

IMAGE_DATA_DIR = Path(__file__).parent / "data/upc_image"


def load_test_image(file_name: str) -> Image.Image:
    file_path = IMAGE_DATA_DIR / file_name
    return Image.open(file_path)


def test_generate_image_fingerprint():
    image_1_url = "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/no_upc1.jpg"
    image_2_url = "https://raw.githubusercontent.com/openfoodfacts/test-data/4a6446c9cac4b279f406fd1e20f8a28b045c823c/robotoff/tests/unit/upc_image/no_upc2.jpg"
    image_1 = download_image(image_1_url)
    image_2 = download_image(image_2_url)
    image_1_rescaled = image_1.copy()
    image_1_rescaled.thumbnail((400, 400))

    fingerprint_1 = generate_image_fingerprint(image_1)
    fingerprint_2 = generate_image_fingerprint(image_2)
    fingerprint_rescaled_1 = generate_image_fingerprint(image_1_rescaled)

    # two different images should have different fingerprints
    assert fingerprint_1 != fingerprint_2
    # fingerprints should be invariant to rescaling
    assert fingerprint_1 == fingerprint_rescaled_1
