import enum
import gzip
import pathlib
import re
import sys
import traceback
from collections import defaultdict

import orjson
import tqdm

MULTIPLE_SPACES_REGEX = re.compile(r" {2,}")


class OCRParsingException(Exception):
    pass


class OCRField(enum.Enum):
    full_text = 1
    full_text_contiguous = 2
    text_annotations = 3


class OCRRegex:
    __slots__ = ("regex", "field", "lowercase", "processing_func", "priority", "notify")

    def __init__(
        self,
        regex,
        field,
        lowercase=False,
        processing_func=None,
        priority=None,
        notify=False,
    ):
        self.regex = regex
        self.field = field
        self.lowercase = lowercase
        self.processing_func = processing_func
        self.priority = priority
        self.notify = notify


class ImageOrientation(enum.Enum):
    up = 1  # intended orientation
    down = 2  # 180° rotation
    left = 3  # 90° counterclockwise rotation
    right = 4  # 90° clockwise rotation
    unknown = 5


class OrientationResult:
    __slots__ = ("count", "orientation")

    def __init__(self, count):
        most_common_list = count.most_common(1)

        if most_common_list:
            self.orientation = most_common_list[0][0]
        else:
            self.orientation = ImageOrientation.unknown

        self.count = {key.name: value for key, value in count.items()}

    def to_json(self):
        return {
            "count": self.count,
            "orientation": self.orientation.name,
        }


class OCRResult:
    __slots__ = (
        "text_annotations",
        "text_annotations_str",
        "text_annotations_str_lower",
        "text_annotations_continuous_str",
        "text_annotations_continuous_str_lower",
        "full_text_annotation",
        "logo_annotations",
        "safe_search_annotation",
        "label_annotations",
        "face_annotations",
    )

    def __init__(self, data, lazy=True):
        self.text_annotations = []
        self.full_text_annotation = None
        self.logo_annotations = []
        self.label_annotations = []
        self.safe_search_annotation = None
        self.face_annotations = []

        for text_annotation_data in data.get("textAnnotations", []):
            text_annotation = OCRTextAnnotation(text_annotation_data)
            self.text_annotations.append(text_annotation)

        self.text_annotations_str = ""
        self.text_annotations_str_lower = ""

        if self.text_annotations:
            self.text_annotations_str = self.text_annotations[0].text
            self.text_annotations_str_lower = self.text_annotations_str.lower()
            self.text_annotations_continuous_str = MULTIPLE_SPACES_REGEX.sub(
                " ", self.text_annotations_str.replace("\n", " ")
            )
            self.text_annotations_continuous_str_lower = (
                self.text_annotations_continuous_str.lower()
            )

        full_text_annotation_data = data.get("fullTextAnnotation")

        if full_text_annotation_data:
            self.full_text_annotation = OCRFullTextAnnotation(
                full_text_annotation_data, lazy=lazy
            )

        for logo_annotation_data in data.get("logoAnnotations", []):
            logo_annotation = LogoAnnotation(logo_annotation_data)
            self.logo_annotations.append(logo_annotation)

        for label_annotation_data in data.get("labelAnnotations", []):
            label_annotation = LabelAnnotation(label_annotation_data)
            self.label_annotations.append(label_annotation)

        if "safeSearchAnnotation" in data:
            self.safe_search_annotation = SafeSearchAnnotation(
                data["safeSearchAnnotation"]
            )

        for face_annotation_data in data.get("faceAnnotations", []):
            face_annotation = FaceAnnotation(face_annotation_data)
            self.face_annotations.append(face_annotation)

    def get_full_text(self, lowercase=False):
        if self.full_text_annotation is not None:
            if lowercase:
                return self.full_text_annotation.text_lower

            return self.full_text_annotation.text

        return ""

    def get_full_text_contiguous(self, lowercase=False):
        if self.full_text_annotation is not None:
            if lowercase:
                return self.full_text_annotation.contiguous_text_lower

            return self.full_text_annotation.contiguous_text

        return ""

    def get_text_annotations(self, lowercase=False):
        if lowercase:
            return self.text_annotations_str_lower
        else:
            return self.text_annotations_str

    def get_text_annotations_contiguous(self, lowercase=False):
        if lowercase:
            return self.text_annotations_continuous_str_lower
        else:
            return self.text_annotations_continuous_str

    def _get_text(self, field, lowercase):
        if field == OCRField.full_text:
            text = self.get_full_text(lowercase)

            if text is None:
                # If there is no full text, get text annotations as fallback
                return self.get_text_annotations(lowercase)
            else:
                return text

        elif field == OCRField.full_text_contiguous:
            text = self.get_full_text_contiguous(lowercase)

            if text is None:
                # If there is no full text, get text annotations as fallback
                return self.get_text_annotations_contiguous(lowercase)
            else:
                return text

        elif field == OCRField.text_annotations:
            return self.get_text_annotations(lowercase)

        else:
            raise ValueError("invalid field: {}".format(field))

    def get_text(self, ocr_regex):
        return self._get_text(ocr_regex.field, ocr_regex.lowercase)

    def get_logo_annotations(self):
        return self.logo_annotations

    def get_label_annotations(self):
        return self.label_annotations

    def get_safe_search_annotation(self):
        return self.safe_search_annotation

    def get_face_annotations(self):
        return self.face_annotations

    @classmethod
    def from_json(cls, data, **kwargs):
        responses = data.get("responses", [])

        if not responses:
            return None

        try:
            response = responses[0]
        except IndexError:
            return None

        if "error" in response:
            print("error in OCR response: " "{}".format(response["error"]))
            return None

        try:
            return OCRResult(response, **kwargs)
        except Exception as e:
            raise OCRParsingException("error during OCR parsing") from e

    def get_languages(self):
        if self.full_text_annotation is not None:
            return self.full_text_annotation.get_languages()

        return None


def get_text(
    content,
    ocr_regex,
    lowercase,
):
    if isinstance(content, str):
        if ocr_regex and ocr_regex.lowercase:
            return content.lower()

        return content.lower() if lowercase else content

    elif isinstance(content, OCRResult):
        if ocr_regex:
            return content.get_text(ocr_regex)
        else:
            text = content.get_full_text_contiguous(lowercase=lowercase)

            if not text:
                text = content.get_text_annotations(lowercase=lowercase)

            return text

    raise TypeError("invalid type: {}".format(type(content)))


class OCRFullTextAnnotation:
    __slots__ = (
        "text",
        "text_lower",
        "_pages",
        "_pages_data",
        "contiguous_text",
        "contiguous_text_lower",
    )

    def __init__(self, data, lazy=True):
        self.text = MULTIPLE_SPACES_REGEX.sub(" ", data["text"])
        self.text_lower = self.text.lower()
        self.contiguous_text = self.text.replace("\n", " ")
        self.contiguous_text = MULTIPLE_SPACES_REGEX.sub(" ", self.contiguous_text)
        self.contiguous_text_lower = self.contiguous_text.lower()
        self._pages_data = data["pages"]
        self._pages = []

        if not lazy:
            self.load_pages()

    def get_languages(self):
        counts = defaultdict(int)
        for page in self.pages:
            page_counts = page.get_languages()

            for key, value in page_counts.items():
                counts[key] += value

        return dict(counts)

    @property
    def pages(self):
        if self._pages_data is not None:
            self.load_pages()

        return self._pages

    def load_pages(self):
        self._pages = [TextAnnotationPage(page) for page in self._pages_data]
        self._pages_data = None


class TextAnnotationPage:
    def __init__(self, data):
        self.width = data["width"]
        self.height = data["height"]
        self.blocks = [Block(d) for d in data["blocks"]]

    def get_languages(self):
        counts = defaultdict(int)
        for block in self.blocks:
            block_counts = block.get_languages()

            for key, value in block_counts.items():
                counts[key] += value

        return dict(counts)


class Block:
    def __init__(self, data):
        self.type = data["blockType"]
        self.paragraphs = [Paragraph(paragraph) for paragraph in data["paragraphs"]]

        self.bounding_poly = None
        if "boundingBox" in data:
            self.bounding_poly = BoundingPoly(data["boundingBox"])

    def get_languages(self):
        counts = defaultdict(int)
        for paragraph in self.paragraphs:
            paragraph_counts = paragraph.get_languages()

            for key, value in paragraph_counts.items():
                counts[key] += value

        return dict(counts)


class Paragraph:
    def __init__(self, data):
        self.words = [Word(word) for word in data["words"]]

        self.bounding_poly = None
        if "boundingBox" in data:
            self.bounding_poly = BoundingPoly(data["boundingBox"])

    def get_languages(self):
        counts = defaultdict(int)

        for word in self.words:
            if word.languages is not None:
                for language in word.languages:
                    counts[language.language] += 1
            else:
                counts["null"] += 1

        counts["words"] = len(self.words)
        return dict(counts)

    def get_text(self):
        """Return the text of the paragraph, by concatenating the words."""
        return "".join(w.text for w in self.words)


class Word:
    __slots__ = ("bounding_poly", "symbols", "languages")

    def __init__(self, data):
        self.bounding_poly = BoundingPoly(data["boundingBox"])
        self.symbols = [Symbol(s) for s in data["symbols"]]

        self.languages = None
        word_property = data.get("property", {})

        if "detectedLanguages" in word_property:
            self.languages = [
                DetectedLanguage(lang) for lang in data["property"]["detectedLanguages"]
            ]

    def get_text(self):
        text_list = []
        for symbol in self.symbols:
            symbol_str = ""

            if symbol.symbol_break and symbol.symbol_break.is_prefix:
                symbol_str = symbol.symbol_break.get_value()

            symbol_str += symbol.text

            if symbol.symbol_break and not symbol.symbol_break.is_prefix:
                symbol_str += symbol.symbol_break.get_value()

            text_list.append(symbol_str)

        return "".join(text_list)


class Symbol:
    __slots__ = ("bounding_poly", "text", "confidence", "symbol_break")

    def __init__(self, data):
        self.bounding_poly = None
        if "boundingBox" in data:
            self.bounding_poly = BoundingPoly(data["boundingBox"])

        self.text = data["text"]
        self.confidence = data.get("confidence", None)

        self.symbol_break = None
        symbol_property = data.get("property", {})

        if "detectedBreak" in symbol_property:
            self.symbol_break = DetectedBreak(symbol_property["detectedBreak"])


class DetectedBreak:
    __slots__ = ("type", "is_prefix")

    def __init__(self, data):
        self.type = data["type"]
        self.is_prefix = data.get("isPrefix", False)

    def __repr__(self):
        return "<DetectedBreak {}>".format(self.type)

    def get_value(self):
        if self.type in ("UNKNOWN", "HYPHEN"):
            return ""

        elif self.type in ("SPACE", "SURE_SPACE", "EOL_SURE_SPACE"):
            return " "

        elif self.type == "LINE_BREAK":
            return "\n"

        else:
            raise ValueError("unknown type: {}".format(self.type))


class DetectedLanguage:
    __slots__ = ("language", "confidence")

    def __init__(self, data):
        self.language = data["languageCode"]
        self.confidence = data.get("confidence", 0)

    def __repr__(self):
        return "<DetectedLanguage: {} (confidence: {})>".format(
            self.language, self.confidence
        )


class BoundingPoly:
    __slots__ = ("vertices",)

    def __init__(self, data):
        self.vertices = [
            (point.get("x", 0), point.get("y", 0)) for point in data["vertices"]
        ]


class OCRTextAnnotation:
    __slots__ = ("locale", "text", "bounding_poly")

    def __init__(self, data):
        self.locale = data.get("locale")
        self.text = data["description"]
        self.bounding_poly = BoundingPoly(data["boundingPoly"])


class LogoAnnotation:
    __slots__ = ("id", "description", "score")

    def __init__(self, data):
        self.id = data.get("mid") or None
        self.score = data["score"]
        self.description = data["description"]


class LabelAnnotation:
    __slots__ = ("id", "description", "score")

    def __init__(self, data):
        self.id = data.get("mid") or None
        self.score = data["score"]
        self.description = data["description"]


class FaceAnnotation:
    __slots__ = (
        "detection_confidence",
        "joy_likelihood",
        "sorrow_likelihood",
        "anger_likelihood",
        "surprise_likelihood",
        "under_exposed_likelihood",
        "blurred_likelihood",
        "headwear_likelihood",
    )

    def __init__(self, data):
        self.detection_confidence = data.get("detectionConfidence", 0.0)
        self.joy_likelihood = SafeSearchAnnotationLikelihood[
            data.get("joyLikelihood", "UNKNOWN")
        ]
        self.sorrow_likelihood = SafeSearchAnnotationLikelihood[
            data.get("sorrowLikelihood", "UNKNOWN")
        ]
        self.anger_likelihood = SafeSearchAnnotationLikelihood[
            data.get("angerLikelihood", "UNKNOWN")
        ]
        self.surprise_likelihood = SafeSearchAnnotationLikelihood[
            data.get("surpriseLikelihood", "UNKNOWN")
        ]
        self.under_exposed_likelihood = SafeSearchAnnotationLikelihood[
            data.get("underExposedLikelihood", "UNKNOWN")
        ]
        self.blurred_likelihood = SafeSearchAnnotationLikelihood[
            data.get("blurredLikelihood", "UNKNOWN")
        ]
        self.headwear_likelihood = SafeSearchAnnotationLikelihood[
            data.get("headwearLikelihood", "UNKNOWN")
        ]


class SafeSearchAnnotation:
    __slots__ = ("adult", "spoof", "medical", "violence", "racy")

    def __init__(self, data):
        self.adult = SafeSearchAnnotationLikelihood[data["adult"]]
        self.spoof = SafeSearchAnnotationLikelihood[data["spoof"]]
        self.medical = SafeSearchAnnotationLikelihood[data["medical"]]
        self.violence = SafeSearchAnnotationLikelihood[data["violence"]]
        self.racy = SafeSearchAnnotationLikelihood[data["racy"]]


class SafeSearchAnnotationLikelihood(enum.IntEnum):
    UNKNOWN = 1
    VERY_UNLIKELY = 2
    UNLIKELY = 3
    POSSIBLE = 4
    LIKELY = 5
    VERY_LIKELY = 6


def extract_ocr_text(input_path, output_path):
    with gzip.open(str(input_path), "rt", encoding="utf-8") as f:
        with gzip.open(str(output_path), "wb") as g:
            for line in tqdm.tqdm(f):
                try:
                    data = orjson.loads(line)
                except orjson.JSONDecodeError as e:
                    print("Error during JSON decode: {}".format(e))
                    continue

                ocr_result_data = data.pop("content")
                try:
                    ocr_result = OCRResult.from_json(ocr_result_data)
                except OCRParsingException:
                    tb = traceback.format_exc()
                    print(tb)
                    continue

                if ocr_result is not None:
                    text = ocr_result._get_text(OCRField.full_text, False)

                    if text:
                        g.write(orjson.dumps({**data, "text": text}) + b"\n")


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.input.is_file():
        sys.exit("input file {} does not exist".format(args.input))
    extract_ocr_text(args.input, args.output)
