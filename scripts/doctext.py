import argparse
import json
import pathlib
import tempfile
from enum import Enum
from typing import Optional, List

import requests
from PIL import Image, ImageDraw

from robotoff.insights.ocr import OCRResult
from robotoff.insights.ocr.dataclass import BoundingPoly


class FeatureType(Enum):
    PAGE = 1
    BLOCK = 2
    PARA = 3
    WORD = 4
    SYMBOL = 5


def draw_boxes(image,
               bounds: List[BoundingPoly],
               color,
               draw_line: bool = False):
    """Draw a border around the image using the hints in the vector list."""
    draw = ImageDraw.Draw(image)

    for bound in bounds:
        draw.polygon([
            bound.vertices[0][0], bound.vertices[0][1],
            bound.vertices[1][0], bound.vertices[1][1],
            bound.vertices[2][0], bound.vertices[2][1],
            bound.vertices[3][0], bound.vertices[3][1]], None, color)

        if draw_line:
            draw.line(bound.get_direction_vector())
    return image


def get_document_bounds(feature: FeatureType,
                        ocr_result: OCRResult):
    """Returns document bounds given an image."""
    bounds = []

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

        if feature == FeatureType.PAGE:
            bounds.append(block.bounding_poly)

    # The list `bounds` contains the coordinates of the bounding boxes.
    return bounds


def find_words():
    pass


def render_doc_text(image_path: pathlib.Path,
                    json_path: pathlib.Path,
                    output_path: Optional[pathlib.Path] = None):
    image = Image.open(image_path)

    with json_path.open('r') as f:
        data = json.load(f)
        ocr_result = OCRResult.from_json(data)

    bounds = get_document_bounds(FeatureType.PAGE, ocr_result)
    draw_boxes(image, bounds, 'blue')
    bounds = get_document_bounds(FeatureType.PARA, ocr_result)
    draw_boxes(image, bounds, 'red')
    bounds = get_document_bounds(FeatureType.WORD, ocr_result)
    draw_boxes(image, bounds, 'yellow', draw_line=True)

    if output_path is not None:
        image.save(output_path)
    else:
        image.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('image_url', help='The image URL for text detection.')
    parser.add_argument('--output-path', help='Optional output file', type=pathlib.Path)
    args = parser.parse_args()

    image_url = args.image_url
    json_url = image_url.replace('.jpg', '.json')

    temp_dir = pathlib.Path(tempfile.mkdtemp())

    image_path = temp_dir / 'image.jpg'
    json_path = temp_dir / 'OCR.json'

    r = requests.get(image_url)

    with image_path.open('wb') as f:
        f.write(r.content)

    r = requests.get(json_url)

    with json_path.open('wb') as f:
        f.write(r.content)

    render_doc_text(image_path, json_path)

