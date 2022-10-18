import gzip
import glob
import orjson
import os
from pathlib import Path


def is_valid_dir(product_dir: str) -> bool:
    product_dir = product_dir[len("/srv2/off/html/images/products") :]  # noqa: E203
    return product_dir.replace("/", "").isdigit()


ROOT_DIR = Path("/srv2/off/html/images/products")
OUTPUT_PATH = Path("/srv2/off/html/data/ocr.jsonl.gz")
added = 0

with gzip.open(str(OUTPUT_PATH), "wb") as output_f:
    for i, image_path_str in enumerate(
        glob.iglob("{}/**/*.jpg".format(ROOT_DIR), recursive=True)
    ):
        if i % 1000 == 0:
            print("step: {}, added: {}".format(i, added))

        image_path = Path(image_path_str)
        if not is_valid_dir(str(image_path.parent)) or not image_path.stem.isdigit():
            continue

        json_path = image_path.with_suffix(".json")
        gz_json_path = image_path.with_suffix(".json.gz")
        gzip_selected = False

        if gz_json_path.is_file() and json_path.is_file():
            assert gz_json_path.stat().st_size
            if os.path.getmtime(str(gz_json_path)) > os.path.getmtime(str(json_path)):
                print("Gzipped version more recent, deleting {}".format(json_path))
                json_path.unlink()
                gzip_selected = True
            else:
                print("Gzipped version less recent: {}".format(gz_json_path))
        elif gz_json_path.is_file():
            gzip_selected = True
        elif json_path.is_file():
            gzip_selected = False
        else:
            continue

        open_fn = gzip.open if gzip_selected else open
        file_path = gz_json_path if gzip_selected else json_path
        with open_fn(str(file_path), "rb") as f:
            try:
                data = orjson.loads(f.read())
            except orjson.JSONDecodeError:
                print("JSON decode error on {}".format(json_path))
                continue

        has_error = False
        for response in data["responses"]:
            if "error" in response:
                has_error = True
                break

        if has_error:
            print("OCR error on {}".format(json_path))
            continue

        output_json = {
            "source": str(image_path)[30:],
            "content": data,
            "created_at": os.path.getmtime(str(image_path)),
        }
        output_f.write(orjson.dumps(output_json) + b"\n")
        added += 1
