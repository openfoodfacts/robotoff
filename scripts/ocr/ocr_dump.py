import gzip
import json
import os
import pathlib


def is_valid_dir(product_dir: str) -> bool:
    product_dir = product_dir[len("/srv2/off/html/images/products") :]  # noqa: E203
    return product_dir.replace("/", "").isdigit()


ROOT_DIR = pathlib.Path("/srv2/off/html/images/products")
OCR_ERROR_PATH = pathlib.Path("~/ocr_error.txt").expanduser()
OUTPUT_PATH = pathlib.Path("/srv2/off/html/data/ocr.jsonl.gz")
added = 0

with gzip.open(str(OUTPUT_PATH), "wt", encoding="utf-8") as output_f:
    for i, image_path in enumerate(ROOT_DIR.glob("**/*.json")):
        if not is_valid_dir(str(image_path.parent)) or not image_path.stem.isdigit():
            continue

        json_path = image_path.with_suffix(".json")

        if not json_path.is_file():
            continue

        with json_path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        has_error = False
        for response in data["responses"]:
            if "error" in response:
                with OCR_ERROR_PATH.open("a", encoding="utf-8") as f:
                    f.write("{}\n".format(json_path))

                has_error = True
                break

        if has_error:
            continue

        output_json = {
            "source": str(image_path)[30:],
            "content": data,
            "created_at": os.path.getmtime(str(image_path)),
        }
        output_f.write(json.dumps(output_json) + "\n")
        added += 1

        if i % 1000 == 0:
            print("step: {}, added: {}".format(i, added))
