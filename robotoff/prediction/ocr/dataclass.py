import enum
import itertools
import math
import operator
import re
from collections import Counter, defaultdict
from typing import Callable, Optional, Union

from robotoff.types import JSONType
from robotoff.utils import get_logger
from robotoff.utils.text import strip_accents_v2

# Some classes documentation were adapted from Google documentation on
# https://cloud.google.com/vision/docs/reference/rpc/google.cloud.vision.v1#google.cloud.vision.v1.Symbol


logger = get_logger(__name__)


class OCRParsingException(Exception):
    pass


class OCRField(enum.Enum):
    """OCR field to use to perform string search.

    full_text: non-contiguous text, a line-break between blocks prevent
        matches spanning several blocks.
    full_text_contiguous: contiguous text, matches spanning several blocks
        are possible
    """

    full_text = 1
    full_text_contiguous = 2


class OCRRegex:
    __slots__ = ("regex", "field", "processing_func", "priority", "notify")

    def __init__(
        self,
        regex: re.Pattern,
        field: OCRField,
        processing_func: Optional[Callable] = None,
        priority: Optional[int] = None,
        notify: bool = False,
    ):
        self.regex: re.Pattern = regex
        self.field: OCRField = field
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
        "full_text_annotation",
        "logo_annotations",
        "safe_search_annotation",
        "label_annotations",
    )

    def __init__(self, data: JSONType):
        self.text_annotations: list[OCRTextAnnotation] = []
        self.full_text_annotation: Optional[OCRFullTextAnnotation] = None
        self.logo_annotations: list[LogoAnnotation] = []
        self.label_annotations: list[LabelAnnotation] = []
        self.safe_search_annotation: Optional[SafeSearchAnnotation] = None

        for text_annotation_data in data.get("textAnnotations", []):
            text_annotation = OCRTextAnnotation(text_annotation_data)
            self.text_annotations.append(text_annotation)

        self.text_annotations_str: str = ""

        if self.text_annotations:
            self.text_annotations_str = self.text_annotations[0].text

        full_text_annotation_data = data.get("fullTextAnnotation")

        if full_text_annotation_data:
            self.full_text_annotation = OCRFullTextAnnotation(full_text_annotation_data)

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

    def get_full_text(self) -> str:
        return (
            self.full_text_annotation.text
            if self.full_text_annotation is not None
            else ""
        )

    def get_full_text_contiguous(self) -> str:
        return (
            self.full_text_annotation.continuous_text
            if self.full_text_annotation is not None
            else ""
        )

    def get_text_annotations(self) -> str:
        return self.text_annotations_str

    def _get_text(self, field: OCRField) -> str:
        if field == OCRField.full_text:
            return self.get_full_text()

        elif field == OCRField.full_text_contiguous:
            return self.get_full_text_contiguous()

        else:
            raise ValueError(f"invalid field: {field}")

    def get_text(self, ocr_regex: OCRRegex) -> str:
        """Return the OCR text.

        If full text annotations are not available, an empty string is
        returned.
        """
        return self._get_text(ocr_regex.field)

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

    def match(
        self,
        pattern: str,
        preprocess_func: Optional[Callable[[str], str]] = None,
        strip_characters: Optional[str] = None,
    ) -> Optional[list[list["Word"]]]:
        """Find the words in the image that match the pattern words in the
        same order.

        Return None if full text annotations are not available.
        See `Paragraph.match` for more details.
        """
        if self.full_text_annotation:
            return self.full_text_annotation.match(
                pattern, preprocess_func, strip_characters
            )
        return None


def get_text(
    content: Union[OCRResult, str], ocr_regex: Optional[OCRRegex] = None
) -> str:
    if isinstance(content, str):
        return content

    elif isinstance(content, OCRResult):
        if ocr_regex:
            return content.get_text(ocr_regex)
        else:
            text = content.get_full_text_contiguous()

            if not text:
                text = content.get_text_annotations()

            return text

    raise TypeError("invalid type: {}".format(type(content)))


class OCRFullTextAnnotation:
    """TextAnnotation contains a structured representation of OCR extracted
    text. The hierarchy of an OCR extracted text structure is like this:
    TextAnnotation -> Page -> Block -> Paragraph -> Word -> Symbol Each
    structural component, starting from Page, may further have their own
    properties. Properties describe detected languages, breaks etc.."""

    __slots__ = (
        "api_text",
        "text",
        "continuous_text",
        "unnaccented_text",
        "pages",
    )

    def __init__(self, data: JSONType):
        # Full text as returned by Google Cloud Vision API
        # We don't use it anymore, we now compute the text directly from
        # page -> block -> paragraph -> word -> symbol, as it allows us to
        # know the location of every matched string
        self.api_text: str = data["text"]
        self.pages: list[TextAnnotationPage] = []
        # `initial_offset` is used to keep track of how many string characters
        # were in the previous page, this is necessary to know where the words
        # are located on the image during matching
        initial_offset = 0
        text_list: list[str] = []
        for page_data in data["pages"]:
            page = TextAnnotationPage(page_data, initial_offset=initial_offset)
            # we add + 1 to offset as we introduce a `|` character to split
            # pages
            initial_offset += len(page.text) + 1
            text_list.append(page.text)
            self.pages.append(page)
        # Join page texts with a `|` character, to avoid matches to span over
        # multiple pages
        self.text: str = "|".join(text_list)
        # Replace line break with space characters to allow matches spanning
        # multiple lines
        # We used to replace consecutive spaces (2+) with a single space so that
        # spurious spaces don't prevent a match, but this is unnecessary: on
        # several millions OCRs, only a few had double spaces, and it was images
        # containing mixed arabic/latin language texts.
        # This way, the word offsets (word.start_idx, word.end_idx) match the
        # FullTextAnnotation text, and we can very easily determine the position
        # of the matched words
        self.continuous_text: str = "|".join(
            t.replace("|", " ").replace("\n", " ") for t in text_list
        )
        # Here we use a accent stripping function that don't delete or
        # introduce any character, so that word offsets are preserved
        self.unnaccented_text = strip_accents_v2(self.continuous_text, keep_length=True)

    def get_languages(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for page in self.pages:
            page_counts = page.get_languages()

            for key, value in page_counts.items():
                counts[key] += value

        return dict(counts)

    def detect_orientation(self) -> OrientationResult:
        word_orientations: list[ImageOrientation] = []

        for page in self.pages:
            word_orientations += page.detect_words_orientation()

        count = Counter(word_orientations)
        return OrientationResult(count)

    def match(
        self,
        pattern: str,
        preprocess_func: Optional[Callable[[str], str]] = None,
        strip_characters: Optional[str] = None,
    ) -> list[list["Word"]]:
        """Find the words in the image that match the pattern words in the
        same order.

        See `Paragraph.match` for more details.
        """
        return list(
            itertools.chain.from_iterable(
                page.match(pattern, preprocess_func, strip_characters)
                for page in self.pages
            )
        )


class TextAnnotationPage:
    """Detected page from OCR."""

    __slots__ = (
        "width",
        "height",
        "blocks",
        "text",
    )

    def __init__(self, data: JSONType, initial_offset: int = 0):
        """Initialize a TextAnnotationPage.

        :param data: the page JSON data from the OCR result
        :param initial_offset: the total number of string characters that
            were contained in previous pages, it's used for matching. Defaults
            to 0.
        """
        self.width = data["width"]
        self.height = data["height"]
        self.blocks: list[Block] = []
        text_list: list[str] = []
        for block_data in data["blocks"]:
            block = Block(block_data, initial_offset)
            # We add a '|' between each block, so that it's not possible to
            # match over several blocks, so we add + 1 to offset
            initial_offset += len(block.text) + 1
            text_list.append(block.text)
            self.blocks.append(block)
        self.text = "|".join(text_list)

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

    def match(
        self,
        pattern: str,
        preprocess_func: Optional[Callable[[str], str]] = None,
        strip_characters: Optional[str] = None,
    ) -> list[list["Word"]]:
        """Find the words in the page that match the pattern words in the
        same order.

        See `Paragraph.match` for more details.
        """
        return list(
            itertools.chain.from_iterable(
                block.match(pattern, preprocess_func, strip_characters)
                for block in self.blocks
            )
        )


class Block:
    """Logical element on the page."""

    __slots__ = (
        "type",
        "paragraphs",
        "text",
        "bounding_poly",
    )

    def __init__(self, data: JSONType, initial_offset: int = 0):
        """Initialize a Block.

        :param data: the block JSON data from the OCR result
        :param initial_offset: the total number of string characters that
            were contained in previous blocks, it's used for matching.
            Defaults to 0.
        """
        self.type = data["blockType"]
        self.paragraphs: list[Paragraph] = []
        text_list = []
        add_space_prefix = False
        for paragraph_data in data["paragraphs"]:
            paragraph = Paragraph(paragraph_data, initial_offset)
            # We split paragraphs with a space character, so add +1 to offset
            initial_offset += len(paragraph.text) + 1
            self.paragraphs.append(paragraph)
            if add_space_prefix:
                text_list.append(" ")
            text_list.append(paragraph.text)
            # We add a space to the next paragraph if the current paragraph is
            # not empty and if it doesn't already end with a space or line break
            add_space_prefix = bool(paragraph.text) and paragraph.text[-1] not in (
                " ",
                "\n",
            )
        self.text: str = "".join(text_list)

        self.bounding_poly = None
        if "boundingBox" in data:
            self.bounding_poly = BoundingPoly(data["boundingBox"])

    def get_words(self):
        return list(
            itertools.chain.from_iterable(
                paragraph.words for paragraph in self.paragraphs
            )
        )

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

    def match(
        self,
        pattern: str,
        preprocess_func: Optional[Callable[[str], str]] = None,
        strip_characters: Optional[str] = None,
    ) -> list[list["Word"]]:
        """Find the words in the block that match the pattern words in the
        same order.

        See `Paragraph.match` for more details.
        """
        return list(
            itertools.chain.from_iterable(
                paragraph.match(pattern, preprocess_func, strip_characters)
                for paragraph in self.paragraphs
            )
        )


class Paragraph:
    """Structural unit of text representing a number of words in certain
    order."""

    __slots__ = (
        "words",
        "text",
        "bounding_poly",
    )

    def __init__(self, data: JSONType, initial_offset: int = 0):
        """Initialize a Paragraph.

        :param data: the paragraph JSON data from the OCR result
        :param initial_offset: the total number of string characters that
            were contained in previous paragraphs, it's used for matching.
            Defaults to 0.
        """
        self.words: list[Word] = []

        offset = initial_offset
        for word_data in data["words"]:
            word = Word(word_data, offset)
            self.words.append(word)
            offset += len(word.text)

        self.text: str = "".join(w.text for w in self.words)
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
        return "".join(w.text for w in self.words)

    def match(
        self,
        pattern: str,
        preprocess_func: Optional[Callable[[str], str]] = None,
        strip_characters: Optional[str] = None,
    ) -> list[list["Word"]]:
        """Find the words in the paragraph that match the pattern words in
        the same order.

        The pattern is first splitted with a whitespace word delimiter, then
        we iterate over both the words and the pattern words to find matches.

        See `Word.match` for a description of `preprocess_func` and
        `strip_characters` parameters or for more details about the matching
        process.

        :param pattern: the string pattern to look for
        :return: a list of word lists, each item in the upper list is a
            different match
        """
        pattern_words = pattern.split()
        matches = []
        # Iterate over the words
        for word_idx in range(len(self.words)):
            current_word = self.words[word_idx]
            stack = list(pattern_words)
            matched_words = []
            while stack:
                pattern_word = stack.pop(0)
                # if words don't match or if there is no word left while the
                # pattern stack is not empty, there is no match: break to
                # continue to next word
                if not current_word.match(
                    pattern_word, preprocess_func, strip_characters
                ) or word_idx + 1 >= len(self.words):
                    break
                matched_words.append(current_word)
                # there is a partial match, continue to next word to see if
                # there is a full match
                word_idx += 1
                current_word = self.words[word_idx]
            else:
                # No break occured, so it's a full match
                matches.append(matched_words)

        return matches


class Word:
    """A word representation."""

    __slots__ = (
        "bounding_poly",
        "symbols",
        "languages",
        "text",
        "start_idx",
        "end_idx",
    )

    def __init__(self, data: JSONType, offset: int = 0):
        """Initialize a Word.

        :param data: the word JSON data from the OCR result
        :param initial_offset: the total number of string characters that
            were contained in previous words, it's used for matching.
            Defaults to 0.
        """
        self.bounding_poly = BoundingPoly(data["boundingBox"])
        self.symbols: list[Symbol] = [Symbol(s) for s in data["symbols"]]

        self.languages: Optional[list[DetectedLanguage]] = None
        word_property = data.get("property", {})

        if "detectedLanguages" in word_property:
            self.languages = [
                DetectedLanguage(lang) for lang in data["property"]["detectedLanguages"]
            ]

        # Attribute to store text generated from symbols
        self.text = self._get_text()
        # start word index on the full OCR text
        self.start_idx = offset
        # end word index on the full OCR text
        self.end_idx = offset + len(self.text)

    def _get_text(self) -> str:
        """Generate the word text from the list of symbols of the word.

        :return: the word text
        """
        text_list = []
        for symbol in self.symbols:
            if symbol.symbol_break and symbol.symbol_break.is_prefix:
                text_list.append(symbol.symbol_break.get_value())
            text_list.append(symbol.text)
            if symbol.symbol_break and not symbol.symbol_break.is_prefix:
                text_list.append(symbol.symbol_break.get_value())

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

    def match(
        self,
        pattern: str,
        preprocess_func: Optional[Callable[[str], str]] = None,
        strip_characters: Optional[str] = None,
    ) -> bool:
        """Return True if the pattern is equal to the word string after
        preprocessing, False otherwise.

        A first preprocessing step is performed before applying
        `preprocess_func` on the word and the pattern: punctuation marks,
        spaces and line breaks are stripped.

        :param pattern: the string to match
        :param preprocess_func: a preprocessing function to apply to pattern
            and word string, defaults to identity function
        :param strip_characters: word characters to strip before matching.
            By default, the following character list is used: "\\n .,!?"
            Pass an empty string to remove any character stripping.
        :return: True if there is a match, False otherwise
        """
        preprocess_func = preprocess_func or (lambda x: x)

        if strip_characters is None:
            strip_characters = "\n .,!?"

        return preprocess_func(self.text.strip(strip_characters)) == preprocess_func(
            pattern.strip(strip_characters)
        )

    def __repr__(self) -> str:
        return f"<Word: {self.text.__repr__()}>"


class Symbol:
    """A single symbol representation."""

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
    """Detected start or end of a structural component."""

    __slots__ = ("type", "is_prefix")

    def __init__(self, data: JSONType):
        # Detected break type.
        # Enum to denote the type of break found. New line, space etc.
        # UNKNOWN: Unknown break label type.
        # SPACE: Regular space.
        # SURE_SPACE: Sure space (very wide).
        # EOL_SURE_SPACE: Line-wrapping break.
        # HYPHEN: End-line hyphen that is not present in text; does not co-occur
        # with SPACE, LEADER_SPACE, or LINE_BREAK.
        # LINE_BREAK: Line break that ends a paragraph.
        self.type = data["type"]
        # True if break prepends the element.
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
