import enum
import operator
import re
from collections import Counter
from typing import Optional, Callable, Dict, List

from robotoff.utils import get_logger
from robotoff.utils.types import JSONType


MULTIPLE_SPACES_REGEX = re.compile(r" {2,}")

logger = get_logger(__name__)


class OCRField(enum.Enum):
    full_text = 1
    full_text_contiguous = 2
    text_annotations = 3


class OCRRegex:
    __slots__ = ('regex', 'field', 'lowercase', 'processing_func',
                 'priority', 'notify')

    def __init__(self, regex,
                 field: OCRField,
                 lowercase: bool = False,
                 processing_func: Optional[Callable] = None,
                 priority: Optional[int] = None,
                 notify: bool = False,
                 trust: float = 1):
        self.regex = regex
        self.field: OCRField = field
        self.lowercase: bool = lowercase
        self.processing_func: Optional[Callable] = processing_func
        self.priority = priority
        self.notify = notify
        self.trust = trust


class ImageOrientation(enum.Enum):
    up = 1  # intended orientation
    down = 2  # 180° rotation
    left = 3  # 90° counterclockwise rotation
    right = 4  # 90° clockwise rotation
    unknown = 5


class OrientationResult:
    __slots__ = ('count', 'orientation')

    def __init__(self, count: Counter):
        most_common_list = count.most_common(1)
        self.orientation: ImageOrientation

        if most_common_list:
            self.orientation = most_common_list[0][0]
        else:
            self.orientation = ImageOrientation.unknown

        self.count: Dict[str, int] = {key.name: value
                                      for key, value in count.items()}

    def to_json(self) -> JSONType:
        return {
            'count': self.count,
            'orientation': self.orientation.name,
        }


class OCRResult:
    __slots__ = ('text_annotations', 'text_annotations_str',
                 'text_annotations_str_lower',
                 'full_text_annotation',
                 'logo_annotations', 'safe_search_annotation',
                 'label_annotations')

    def __init__(self, data: JSONType):
        self.text_annotations: List[OCRTextAnnotation] = []
        self.full_text_annotation: Optional[OCRFullTextAnnotation] = None
        self.logo_annotations: List[LogoAnnotation] = []
        self.label_annotations: List[LabelAnnotation] = []
        self.safe_search_annotation: Optional[SafeSearchAnnotation] = None

        for text_annotation_data in data.get('textAnnotations', []):
            text_annotation = OCRTextAnnotation(text_annotation_data)
            self.text_annotations.append(text_annotation)

        self.text_annotations_str: Optional[str] = None
        self.text_annotations_str_lower: Optional[str] = None

        if self.text_annotations:
            self.text_annotations_str = '||'.join(t.text
                                                  for t in self.text_annotations)
            self.text_annotations_str_lower = (self.text_annotations_str
                                               .lower())

        full_text_annotation_data = data.get('fullTextAnnotation')

        if full_text_annotation_data:
            self.full_text_annotation = OCRFullTextAnnotation(
                full_text_annotation_data)

        for logo_annotation_data in data.get('logoAnnotations', []):
            logo_annotation = LogoAnnotation(logo_annotation_data)
            self.logo_annotations.append(logo_annotation)

        for label_annotation_data in data.get('labelAnnotations', []):
            label_annotation = LabelAnnotation(label_annotation_data)
            self.label_annotations.append(label_annotation)

        if 'safeSearchAnnotation' in data:
            self.safe_search_annotation = SafeSearchAnnotation(
                data['safeSearchAnnotation'])

    def get_full_text(self, lowercase: bool = False) -> Optional[str]:
        if self.full_text_annotation is not None:
            if lowercase:
                return self.full_text_annotation.text_lower

            return self.full_text_annotation.text

        return None

    def get_full_text_contiguous(self, lowercase: bool = False) -> Optional[str]:
        if self.full_text_annotation is not None:
            if lowercase:
                return self.full_text_annotation.contiguous_text_lower

            return self.full_text_annotation.contiguous_text

        return None

    def get_text_annotations(self, lowercase: bool = False) -> Optional[str]:
        if self.text_annotations_str is not None:
            if lowercase:
                return self.text_annotations_str_lower
            else:
                return self.text_annotations_str

    def get_text(self, ocr_regex: OCRRegex) -> Optional[str]:
        field = ocr_regex.field

        if field == OCRField.full_text:
            text = self.get_full_text(ocr_regex.lowercase)

            if text is None:
                # If there is no full text, get text annotations as fallback
                return self.get_text_annotations(ocr_regex.lowercase)
            else:
                return text

        elif field == OCRField.full_text_contiguous:
            text = self.get_full_text_contiguous(ocr_regex.lowercase)

            if text is None:
                # If there is no full text, get text annotations as fallback
                return self.get_text_annotations(ocr_regex.lowercase)
            else:
                return text

        elif field == OCRField.text_annotations:
            return self.get_text_annotations(ocr_regex.lowercase)

        else:
            raise ValueError("invalid field: {}".format(field))

    def get_logo_annotations(self) -> List['LogoAnnotation']:
        return self.logo_annotations

    def get_label_annotations(self) -> List['LabelAnnotation']:
        return self.label_annotations

    def get_safe_search_annotation(self):
        return self.safe_search_annotation

    def get_orientation(self) -> Optional[OrientationResult]:
        if self.full_text_annotation:
            return self.full_text_annotation.detect_orientation()
        else:
            return None

    @classmethod
    def from_json(cls, data: JSONType) -> Optional['OCRResult']:
        responses = data.get('responses', [])

        if not responses:
            return None

        response = responses[0]

        if 'error' in response:
            return None

        return OCRResult(response)


class OCRFullTextAnnotation:
    __slots__ = ('text', 'text_lower',
                 'pages', 'contiguous_text', 'contiguous_text_lower')

    def __init__(self, data: JSONType):
        self.text = MULTIPLE_SPACES_REGEX.sub(' ', data['text'])
        self.text_lower = self.text.lower()
        self.contiguous_text = self.text.replace('\n', ' ')
        self.contiguous_text = MULTIPLE_SPACES_REGEX.sub(' ',
                                                         self.contiguous_text)
        self.contiguous_text_lower = self.contiguous_text.lower()
        self.pages: List[TextAnnotationPage] = [TextAnnotationPage(page)
                                                for page in data['pages']]

    def detect_orientation(self) -> OrientationResult:
        word_orientations: List[ImageOrientation] = []

        for page in self.pages:
            word_orientations += page.detect_words_orientation()

        count = Counter(word_orientations)
        return OrientationResult(count)


class TextAnnotationPage:
    def __init__(self, data: JSONType):
        self.width = data['width']
        self.height = data['height']
        self.blocks = [Block(d) for d in data['blocks']]

    def detect_words_orientation(self) -> List[ImageOrientation]:
        word_orientations: List[ImageOrientation] = []

        for block in self.blocks:
            word_orientations += block.detect_words_orientation()

        return word_orientations


class Block:
    def __init__(self, data: JSONType):
        self.type = data['blockType']
        self.paragraphs = [Paragraph(paragraph)
                           for paragraph in data['paragraphs']]
        self.bounding_poly = BoundingPoly(data['boundingBox'])

    def detect_orientation(self) -> ImageOrientation:
        return self.bounding_poly.detect_orientation()

    def detect_words_orientation(self) -> List[ImageOrientation]:
        word_orientations: List[ImageOrientation] = []

        for paragraph in self.paragraphs:
            word_orientations += paragraph.detect_words_orientation()

        return word_orientations


class Paragraph:
    def __init__(self, data: JSONType):
        self.words = [Word(word) for word in data['words']]
        self.bounding_poly = BoundingPoly(data['boundingBox'])

    def detect_orientation(self) -> ImageOrientation:
        return self.bounding_poly.detect_orientation()

    def detect_words_orientation(self) -> List[ImageOrientation]:
        return [word.detect_orientation() for word in self.words]

    def get_text(self) -> str:
        """Return the text of the paragraph, by concatenating the words."""
        return ''.join(w.get_text() for w in self.words)


class Word:
    __slots__ = ('bounding_poly', 'symbols', 'languages')

    def __init__(self, data: JSONType):
        self.bounding_poly = BoundingPoly(data['boundingBox'])
        self.symbols: List[Symbol] = [Symbol(s) for s in data['symbols']]

        self.languages: Optional[List[DetectedLanguage]] = None
        word_property = data.get('property', {})

        if 'detectedLanguages' in word_property:
            self.languages: List[DetectedLanguage] = [
                DetectedLanguage(l) for l in
                data['property']['detectedLanguages']]

    def get_text(self) -> str:
        text_list = []
        for symbol in self.symbols:
            symbol_str = ''

            if symbol.symbol_break and symbol.symbol_break.is_prefix:
                symbol_str = symbol.symbol_break.get_value()

            symbol_str += symbol.text

            if symbol.symbol_break and not symbol.symbol_break.is_prefix:
                symbol_str += symbol.symbol_break.get_value()

            text_list.append(symbol_str)

        return ''.join(text_list)

    def detect_orientation(self) -> ImageOrientation:
        return self.bounding_poly.detect_orientation()


class Symbol:
    __slots__ = ('bounding_poly', 'text', 'confidence', 'symbol_break')

    def __init__(self, data: JSONType):
        self.bounding_poly = BoundingPoly(data['boundingBox'])
        self.text = data['text']
        self.confidence = data.get('confidence', None)

        self.symbol_break: Optional[DetectedBreak] = None
        symbol_property = data.get('property', {})

        if 'detectedBreak' in symbol_property:
            self.symbol_break = DetectedBreak(
                symbol_property['detectedBreak'])

    def detect_orientation(self) -> ImageOrientation:
        return self.bounding_poly.detect_orientation()


class DetectedBreak:
    __slots__ = ('type', 'is_prefix')

    def __init__(self, data: JSONType):
        self.type = data['type']
        self.is_prefix = data.get('isPrefix', False)

    def __repr__(self):
        return "<DetectedBreak {}>".format(self.type)

    def get_value(self):
        if self.type in ('UNKNOWN', 'HYPHEN'):
            return ''

        elif self.type in ('SPACE', 'SURE_SPACE', 'EOL_SURE_SPACE'):
            return ' '

        elif self.type == 'LINE_BREAK':
            return '\n'

        else:
            raise ValueError("unknown type: {}".format(self.type))


class DetectedLanguage:
    __slots__ = ('language', 'confidence')

    def __init__(self, data: JSONType):
        self.language = data['languageCode']
        self.confidence = data.get('confidence', 0)


class BoundingPoly:
    __slots__ = ('vertices', )

    def __init__(self, data: JSONType):
        self.vertices = [(point.get('x', 0), point.get('y', 0))
                         for point in data['vertices']]

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
        indexed_vertices = [(x[0], x[1], i)
                            for i, x in enumerate(self.vertices)]
        # Sort by ascending y-value and select first two vertices:
        # get the two topmost vertices
        indexed_vertices = sorted(indexed_vertices,
                                  key=operator.itemgetter(1))[:2]

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
            logger.error("Unknown orientation: edge {}, vertices {}"
                         "".format(first_edge, self.vertices))
            return ImageOrientation.unknown


class OCRTextAnnotation:
    __slots__ = ('locale', 'text', 'bounding_poly')

    def __init__(self, data: JSONType):
        self.locale = data.get('locale')
        self.text = data['description']
        self.bounding_poly = BoundingPoly(data['boundingPoly'])


class LogoAnnotation:
    __slots__ = ('id', 'description', 'score')

    def __init__(self, data: JSONType):
        self.id = data.get('mid') or None
        self.score = data['score']
        self.description = data['description']


class LabelAnnotation:
    __slots__ = ('id', 'description', 'score')

    def __init__(self, data: JSONType):
        self.id = data.get('mid') or None
        self.score = data['score']
        self.description = data['description']


class SafeSearchAnnotation:
    __slots__ = ('adult', 'spoof', 'medical', 'violence', 'racy')

    def __init__(self, data: JSONType):
        self.adult: SafeSearchAnnotationLikelihood = \
            SafeSearchAnnotationLikelihood[data['adult']]
        self.spoof: SafeSearchAnnotationLikelihood = \
            SafeSearchAnnotationLikelihood[data['spoof']]
        self.medical: SafeSearchAnnotationLikelihood = \
            SafeSearchAnnotationLikelihood[data['medical']]
        self.violence: SafeSearchAnnotationLikelihood = \
            SafeSearchAnnotationLikelihood[data['violence']]
        self.racy: SafeSearchAnnotationLikelihood = \
            SafeSearchAnnotationLikelihood[data['racy']]


class SafeSearchAnnotationLikelihood(enum.IntEnum):
    UNKNOWN = 1
    VERY_UNLIKELY = 2
    UNLIKELY = 3
    POSSIBLE = 4
    LIKELY = 5
    VERY_LIKELY = 6
