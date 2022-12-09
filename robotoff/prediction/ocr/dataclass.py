import enum
import math
import operator
import re
from collections import Counter, defaultdict
from typing import Callable, Optional, Union

from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

MULTIPLE_SPACES_REGEX = re.compile(r" {2,}")

logger = get_logger(__name__)


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
        regex: re.Pattern,
        field: OCRField,
        lowercase: bool = False,
        processing_func: Optional[Callable] = None,
        priority: Optional[int] = None,
        notify: bool = False,
    ):
        self.regex: re.Pattern = regex
        self.field: OCRField = field
        self.lowercase: bool = lowercase
        self.processing_func: Optional[Callable] = processing_func
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

    def __init__(self, count: Counter):
        most_common_list = count.most_common(1)
        self.orientation: ImageOrientation

        if most_common_list:
            self.orientation = most_common_list[0][0]
        else:
            self.orientation = ImageOrientation.unknown

        self.count: dict[str, int] = {key.name: value for key, value in count.items()}

    def to_json(self) -> JSONType:
        return {
            "count": self.count,
            "orientation": self.orientation.name,
        }


class OCRResultGenerationException(Exception):
    """An Error occurred while analyzing OCR

    args may contain ocr_url"""

    pass


class OCRResult:
    __slots__ = (
        "text_annotations",
        "text_annotations_str",
        "text_annotations_str_lower",
        "full_text_annotation",
        "logo_annotations",
        "safe_search_annotation",
        "label_annotations",
    )

    def __init__(self, data: JSONType, lazy: bool = True):
        self.text_annotations: list[OCRTextAnnotation] = []
        self.full_text_annotation: Optional[OCRFullTextAnnotation] = None
        self.logo_annotations: list[LogoAnnotation] = []
        self.label_annotations: list[LabelAnnotation] = []
        self.safe_search_annotation: Optional[SafeSearchAnnotation] = None

        for text_annotation_data in data.get("textAnnotations", []):
            text_annotation = OCRTextAnnotation(text_annotation_data)
            self.text_annotations.append(text_annotation)

        self.text_annotations_str: str = ""
        self.text_annotations_str_lower: str = ""

        if self.text_annotations:
            self.text_annotations_str = self.text_annotations[0].text
            self.text_annotations_str_lower = self.text_annotations_str.lower()

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

    def get_full_text(self, lowercase: bool = False) -> str:
        if self.full_text_annotation is not None:
            if lowercase:
                return self.full_text_annotation.text_lower

            return self.full_text_annotation.text

        return ""

    def get_full_text_contiguous(self, lowercase: bool = False) -> str:
        if self.full_text_annotation is not None:
            if lowercase:
                return self.full_text_annotation.contiguous_text_lower

            return self.full_text_annotation.contiguous_text

        return ""

    def get_text_annotations(self, lowercase: bool = False) -> str:
        if lowercase:
            return self.text_annotations_str_lower
        else:
            return self.text_annotations_str

    def _get_text(self, field: OCRField, lowercase: bool) -> str:
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
                return self.get_text_annotations(lowercase)
            else:
                return text

        elif field == OCRField.text_annotations:
            return self.get_text_annotations(lowercase)

        else:
            raise ValueError("invalid field: {}".format(field))

    def get_text(self, ocr_regex: OCRRegex) -> str:
        return self._get_text(ocr_regex.field, ocr_regex.lowercase)

    def get_logo_annotations(self) -> list["LogoAnnotation"]:
        return self.logo_annotations

    def get_label_annotations(self) -> list["LabelAnnotation"]:
        return self.label_annotations

    def get_safe_search_annotation(self):
        return self.safe_search_annotation

    def get_orientation(self) -> Optional[OrientationResult]:
        if self.full_text_annotation:
            return self.full_text_annotation.detect_orientation()
        else:
            return None

    @classmethod
    def from_json(cls, data: JSONType, **kwargs) -> Optional["OCRResult"]:
        if "responses" not in data or not isinstance(data["responses"], list):
            raise OCRParsingException("Responses field (list) expected in OCR JSON")

        responses = data["responses"]

        if not responses:
            raise OCRParsingException("Empty OCR response")

        response = responses[0]
        if "error" in response:
            raise OCRParsingException(f"Error in OCR response: {response['error']}")

        try:
            return OCRResult(response, **kwargs)
        except Exception as e:
            raise OCRParsingException("Error during OCR parsing") from e

    def get_languages(self) -> Optional[dict[str, int]]:
        if self.full_text_annotation is not None:
            return self.full_text_annotation.get_languages()

        return None


def get_text(
    content: Union[OCRResult, str],
    ocr_regex: Optional[OCRRegex] = None,
    lowercase: bool = True,
) -> str:
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

    def __init__(self, data: JSONType, lazy: bool = True):
        self.text = MULTIPLE_SPACES_REGEX.sub(" ", data["text"])
        self.text_lower = self.text.lower()
        self.contiguous_text = self.text.replace("\n", " ")
        self.contiguous_text = MULTIPLE_SPACES_REGEX.sub(" ", self.contiguous_text)
        self.contiguous_text_lower = self.contiguous_text.lower()
        self._pages_data = data["pages"]
        self._pages: list[TextAnnotationPage] = []

        if not lazy:
            self.load_pages()

    def get_languages(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for page in self.pages:
            page_counts = page.get_languages()

            for key, value in page_counts.items():
                counts[key] += value

        return dict(counts)

    @property
    def pages(self) -> list["TextAnnotationPage"]:
        if self._pages_data is not None:
            self.load_pages()

        return self._pages

    def load_pages(self):
        self._pages = [TextAnnotationPage(page) for page in self._pages_data]
        self._pages_data = None

    def detect_orientation(self) -> OrientationResult:
        word_orientations: list[ImageOrientation] = []

        for page in self.pages:
            word_orientations += page.detect_words_orientation()

        count = Counter(word_orientations)
        return OrientationResult(count)


class TextAnnotationPage:
    def __init__(self, data: JSONType):
        self.width = data["width"]
        self.height = data["height"]
        self.blocks: list[Block] = [Block(d) for d in data["blocks"]]

    def get_languages(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for block in self.blocks:
            block_counts = block.get_languages()

            for key, value in block_counts.items():
                counts[key] += value

        return dict(counts)

    def detect_words_orientation(self) -> list[ImageOrientation]:
        word_orientations: list[ImageOrientation] = []

        for block in self.blocks:
            word_orientations += block.detect_words_orientation()

        return word_orientations


class Block:
    def __init__(self, data: JSONType):
        self.type = data["blockType"]
        self.paragraphs: list[Paragraph] = [
            Paragraph(paragraph) for paragraph in data["paragraphs"]
        ]

        self.bounding_poly = None
        if "boundingBox" in data:
            self.bounding_poly = BoundingPoly(data["boundingBox"])

    def get_languages(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for paragraph in self.paragraphs:
            paragraph_counts = paragraph.get_languages()

            for key, value in paragraph_counts.items():
                counts[key] += value

        return dict(counts)

    def detect_orientation(self) -> Optional[ImageOrientation]:
        if self.bounding_poly:
            return self.bounding_poly.detect_orientation()

        return None

    def detect_words_orientation(self) -> list[ImageOrientation]:
        word_orientations: list[ImageOrientation] = []

        for paragraph in self.paragraphs:
            word_orientations += paragraph.detect_words_orientation()

        return word_orientations


class Paragraph:
    def __init__(self, data: JSONType):
        self.words: list[Word] = [Word(word) for word in data["words"]]

        self.bounding_poly = None
        if "boundingBox" in data:
            self.bounding_poly = BoundingPoly(data["boundingBox"])

    def get_languages(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)

        for word in self.words:
            if word.languages is not None:
                for language in word.languages:
                    counts[language.language] += 1
            else:
                counts["null"] += 1

        counts["words"] = len(self.words)
        return dict(counts)

    def detect_orientation(self) -> Optional[ImageOrientation]:
        if self.bounding_poly:
            return self.bounding_poly.detect_orientation()

        return None

    def detect_words_orientation(self) -> list[ImageOrientation]:
        return [word.detect_orientation() for word in self.words]

    def get_text(self) -> str:
        """Return the text of the paragraph, by concatenating the words."""
        return "".join(w.get_text() for w in self.words)


class Word:
    __slots__ = ("bounding_poly", "symbols", "languages")

    def __init__(self, data: JSONType):
        self.bounding_poly = BoundingPoly(data["boundingBox"])
        self.symbols: list[Symbol] = [Symbol(s) for s in data["symbols"]]

        self.languages: Optional[list[DetectedLanguage]] = None
        word_property = data.get("property", {})

        if "detectedLanguages" in word_property:
            self.languages = [
                DetectedLanguage(lang) for lang in data["property"]["detectedLanguages"]
            ]

    def get_text(self) -> str:
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

    def detect_orientation(self) -> ImageOrientation:
        return self.bounding_poly.detect_orientation()

    def on_same_line(self, word: "Word"):
        (
            self_alpha,
            self_width,
        ) = self.bounding_poly.get_direction_vector_alpha_distance()
        (
            word_alpha,
            word_width,
        ) = word.bounding_poly.get_direction_vector_alpha_distance()
        self_symbol_width = self_width / len(self.symbols)
        word_symbol_width = word_width / len(word.symbols)
        print(
            "Alpha/distance/mean symbol width:",
            self_alpha,
            self_width,
            self_symbol_width,
        )
        print(
            "Alpha/distance/mean symbol width:",
            word_alpha,
            word_width,
            word_symbol_width,
        )


class Symbol:
    __slots__ = ("bounding_poly", "text", "confidence", "symbol_break")

    def __init__(self, data: JSONType):
        self.bounding_poly: Optional[BoundingPoly] = None
        if "boundingBox" in data:
            self.bounding_poly = BoundingPoly(data["boundingBox"])

        self.text = data["text"]
        self.confidence = data.get("confidence", None)

        self.symbol_break: Optional[DetectedBreak] = None
        symbol_property = data.get("property", {})

        if "detectedBreak" in symbol_property:
            self.symbol_break = DetectedBreak(symbol_property["detectedBreak"])

    def detect_orientation(self) -> Optional[ImageOrientation]:
        if self.bounding_poly:
            return self.bounding_poly.detect_orientation()
        return None


class DetectedBreak:
    __slots__ = ("type", "is_prefix")

    def __init__(self, data: JSONType):
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

    def __init__(self, data: JSONType):
        self.language = data["languageCode"]
        self.confidence = data.get("confidence", 0)

    def __repr__(self):
        return "<DetectedLanguage: {} (confidence: {})>".format(
            self.language, self.confidence
        )


class BoundingPoly:
    __slots__ = ("vertices",)

    def __init__(self, data: JSONType):
        self.vertices = [
            (point.get("x", 0), point.get("y", 0)) for point in data["vertices"]
        ]

    def get_direction_vector(self) -> list[tuple[int, int]]:
        left_point = (
            (self.vertices[0][0] + self.vertices[3][0]) / 2,
            (self.vertices[0][1] + self.vertices[3][1]) / 2,
        )
        right_point = (
            (self.vertices[1][0] + self.vertices[2][0]) / 2,
            (self.vertices[1][1] + self.vertices[2][1]) / 2,
        )

        return [left_point, right_point]

    def get_direction_vector_alpha_distance(self) -> tuple[float, float]:
        left_point, right_point = self.get_direction_vector()
        alpha = (right_point[1] - left_point[1]) / (right_point[0] - left_point[0])
        distance = math.sqrt(
            (left_point[0] - right_point[0]) ** 2
            + (left_point[0] - right_point[0]) ** 2
        )
        return alpha, distance

    def detect_orientation(self) -> ImageOrientation:
        """Detect bounding poly orientation (up, down, left, or right).

        Google Vision vertices origin is at the top-left corner of the image.
        The order of each vertex gives the orientation of the text. For
        instance, horizontal text looks like this:
            0----1
            |    |
            3----2
        And left-rotated text looks like this:
            1----2
            |    |
            0----3

        See https://cloud.google.com/vision/docs/reference/rest/v1/images/annotate#Block
        for more details.

        We first select the two higher vertices of the image (lower y-values),
        and order the vertices by ascending x-value.

        This way, the index of these two vertices indicates the text
        orientation:
        - (0, 1) for horizontal (up, standard)
        - (1, 2) for 90° counterclockwise rotation (left)
        - (2, 3) for 180° rotation (down)
        - (3, 0) for 90° clockwise rotation (right)
        It is u
        """
        indexed_vertices = [(x[0], x[1], i) for i, x in enumerate(self.vertices)]
        # Sort by ascending y-value and select first two vertices:
        # get the two topmost vertices
        indexed_vertices = sorted(indexed_vertices, key=operator.itemgetter(1))[:2]

        first_vertex_index = indexed_vertices[0][2]
        second_vertex_index = indexed_vertices[1][2]

        # Sort by index ID, to make sure to filter permutations ((0, 1) and
        # not (1, 0))
        first_edge = tuple(sorted((first_vertex_index, second_vertex_index)))

        if first_edge == (0, 1):
            return ImageOrientation.up

        elif first_edge == (1, 2):
            return ImageOrientation.left

        elif first_edge == (2, 3):
            return ImageOrientation.down

        elif first_edge == (0, 3):
            return ImageOrientation.right

        else:
            logger.error(
                "Unknown orientation: edge %s, vertices %s",
                first_edge,
                self.vertices,
            )
            return ImageOrientation.unknown


class OCRTextAnnotation:
    __slots__ = ("locale", "text", "bounding_poly")

    def __init__(self, data: JSONType):
        self.locale = data.get("locale")
        self.text = data["description"]
        self.bounding_poly = BoundingPoly(data["boundingPoly"])


class LogoAnnotation:
    __slots__ = ("id", "description", "score")

    def __init__(self, data: JSONType):
        self.id = data.get("mid") or None
        self.score = data["score"]
        self.description = data["description"]


class LabelAnnotation:
    __slots__ = ("id", "description", "score")

    def __init__(self, data: JSONType):
        self.id = data.get("mid") or None
        self.score = data["score"]
        self.description = data["description"]


class SafeSearchAnnotation:
    __slots__ = ("adult", "spoof", "medical", "violence", "racy")

    def __init__(self, data: JSONType):
        self.adult: SafeSearchAnnotationLikelihood = SafeSearchAnnotationLikelihood[
            data["adult"]
        ]
        self.spoof: SafeSearchAnnotationLikelihood = SafeSearchAnnotationLikelihood[
            data["spoof"]
        ]
        self.medical: SafeSearchAnnotationLikelihood = SafeSearchAnnotationLikelihood[
            data["medical"]
        ]
        self.violence: SafeSearchAnnotationLikelihood = SafeSearchAnnotationLikelihood[
            data["violence"]
        ]
        self.racy: SafeSearchAnnotationLikelihood = SafeSearchAnnotationLikelihood[
            data["racy"]
        ]


class SafeSearchAnnotationLikelihood(enum.IntEnum):
    UNKNOWN = 1
    VERY_UNLIKELY = 2
    UNLIKELY = 3
    POSSIBLE = 4
    LIKELY = 5
    VERY_LIKELY = 6
