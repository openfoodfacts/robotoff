import argparse
import json
import sys
import tempfile
from enum import Enum
from pathlib import Path
from typing import List, Optional

import requests
from PIL import Image, ImageDraw

from robotoff.prediction.ocr import OCRResult
from robotoff.prediction.ocr.dataclass import BoundingPoly


class FeatureType(Enum):
    PAGE = 1
    BLOCK = 2
    PARA = 3
    WORD = 4
    SYMBOL = 5


def draw_boxes(image, bounds: List[BoundingPoly], color, draw_line: bool = False):
    """Draw a border around the image using the hints in the vector list."""
    draw = ImageDraw.Draw(image)

    for bound in bounds:
        draw.polygon(
            [
                bound.vertices[0][0],
                bound.vertices[0][1],
                bound.vertices[1][0],
                bound.vertices[1][1],
                bound.vertices[2][0],
                bound.vertices[2][1],
                bound.vertices[3][0],
                bound.vertices[3][1],
            ],
            None,
            color,
        )

        if draw_line:
            draw.line(bound.get_direction_vector())
    return image


def get_document_bounds(feature: FeatureType, ocr_result: OCRResult):
    """Returns document bounds given an image."""
    bounds: List[Optional[BoundingPoly]] = []

    document = ocr_result.full_text_annotation

    if document is None:
        return bounds

    # Collect specified feature bounds by enumerating all document features
    for page in document.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    for symbol in word.symbols:
                        if feature == FeatureType.SYMBOL:
                            bounds.append(symbol.bounding_poly)

                    if feature == FeatureType.WORD:
                        bounds.append(word.bounding_poly)

                if feature == FeatureType.PARA:
                    bounds.append(paragraph.bounding_poly)

            if feature == FeatureType.BLOCK:
                bounds.append(block.bounding_poly)

    # The list `bounds` contains the coordinates of the bounding boxes.
    return bounds


def find_words():
    pass


def render_doc_text(
    image_path: Path,
    json_path: Path,
    output_path: Optional[Path] = None,
):
    image = Image.open(image_path)

    with json_path.open("r") as f:
        data = json.load(f)
        ocr_result = OCRResult.from_json(data)

    if ocr_result is None:
        raise ValueError("invalid OCR")

    bounds = get_document_bounds(FeatureType.PAGE, ocr_result)
    draw_boxes(image, bounds, "blue")
    bounds = get_document_bounds(FeatureType.PARA, ocr_result)
    draw_boxes(image, bounds, "red")
    bounds = get_document_bounds(FeatureType.WORD, ocr_result)
    draw_boxes(image, bounds, "yellow", draw_line=True)

    if output_path is not None:
        image.save(output_path)
    else:
        image.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-url", help="The image URL for text detection.")
    parser.add_argument("--image-path", help="The image path.")
    parser.add_argument("--json-path", type=Path)
    parser.add_argument("--output-path", help="Optional output file", type=Path)
    args = parser.parse_args()

    if args.image_url and args.image_path:
        print(
            "--image-url and --image-path are incompatible, choose one of these option"
        )
        sys.exit(1)
    if args.image_path and args.json_path is None:
        print("--json-path must be provided when --image-path is provided")
        sys.exit(1)

    if args.image_path:
        image_path = args.image_path
    else:
        image_url = args.image_url
        temp_dir = Path(tempfile.mkdtemp())

        image_path = temp_dir / "image.jpg"
        json_path = temp_dir / "OCR.json"

        r = requests.get(image_url)

        with image_path.open("wb") as f:
            f.write(r.content)

    if args.json_path is not None:
        json_path = args.json_path
    else:
        json_url = image_url.replace(".jpg", ".json")
        r = requests.get(json_url)

        with json_path.open("wb") as f:
            f.write(r.content)

    render_doc_text(image_path, json_path)
