from robotoff.products import ProductDataset
from robotoff.utils import dump_jsonl, get_logger
from robotoff import settings

logger = get_logger()


def images_dimension_iter():
    dataset = ProductDataset.load()

    for product in dataset.stream().filter_nonempty_text_field("code"):
        images = product.get("images", {})
        for image_id, image_data in images.items():
            if not image_id.isdigit():
                continue

            if "full" not in image_data["sizes"]:
                continue

            width = image_data["sizes"]["full"]["w"]
            height = image_data["sizes"]["full"]["h"]
            yield [int(width), int(height), product["code"], str(image_id)]


dump_jsonl(settings.PROJECT_DIR / "images_dimension.jsonl", images_dimension_iter())
