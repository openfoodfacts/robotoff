# -*- coding: utf-8 -*-
import datetime
import enum
import functools
import gzip
import operator
import re
import json

import pathlib as pathlib
from collections import Counter
from typing import List, Dict, Iterable, Optional, Tuple, Callable, Set
from urllib.parse import urlparse

import requests

from robotoff import settings
from robotoff.insights._enum import InsightType
from robotoff.utils import text_file_iter, get_logger
from robotoff.utils.types import JSONType


logger = get_logger(__name__)


def process_fr_packaging_match(match) -> str:
    approval_numbers = match.group(1, 2, 3)
    return "FR {}.{}.{} EC".format(*approval_numbers).upper()


def process_de_packaging_match(match) -> str:
    federal_state_tag, company_tag = match.group(1, 2)

    return "DE {}-{} EC".format(federal_state_tag,
                                company_tag).upper()


def process_fr_emb_match(match) -> str:
    city_code, company_code = match.group(1, 2)
    city_code = city_code.replace(' ', '')
    company_code = company_code or ''
    return "EMB {}{}".format(city_code,
                             company_code).upper()


def process_eu_bio_label_code(match) -> str:
    return ("en:{}-{}-{}".format(match.group(1),
                                 match.group(2),
                                 match.group(3))
            .lower()
            .replace('ö', 'o')
            .replace('ø', 'o'))


def process_full_digits_expiration_date(match, short: bool) -> Optional[datetime.date]:
    day, month, year = match.group(1, 2, 3)

    if short:
        format_str: str = "%d/%m/%y"
    else:
        format_str = "%d/%m/%Y"

    try:
        date = datetime.datetime.strptime("{}/{}/{}".format(day, month, year), format_str).date()
    except ValueError:
        return None

    return date


def process_product_weight(match, prompt: bool) -> Dict:
    raw = match.group()

    if prompt:
        prompt_str = match.group(1)
        value = match.group(2)
        unit = match.group(3)
    else:
        prompt_str = None
        value = match.group(1)
        unit = match.group(2)

    if unit in ('dle', 'cle', 'mge', 'mle', 'ge', 'kge', 'le'):
        # When the e letter often comes after the weight unit, the
        # space is often not detected
        unit = unit[:-1]

    text = "{} {}".format(value, unit)
    result = {
        'text': text,
        'raw': raw,
        'value': value,
        'unit': unit,
    }

    if prompt_str is not None:
        result['prompt'] = prompt_str

    return result


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
                 notify: bool = False):
        self.regex = regex
        self.field: OCRField = field
        self.lowercase: bool = lowercase
        self.processing_func: Optional[Callable] = processing_func
        self.priority = priority
        self.notify = notify


MULTIPLE_SPACES_REGEX = re.compile(r" {2,}")
BARCODE_PATH_REGEX = re.compile(r"^(...)(...)(...)(.*)$")

PACKAGER_CODE: Dict[str, OCRRegex] = {
    "fr_emb": OCRRegex(re.compile(r"emb ?(\d ?\d ?\d ?\d ?\d) ?([a-z])?(?![a-z0-9])"),
                       field=OCRField.text_annotations,
                       lowercase=True,
                       processing_func=process_fr_emb_match),
    "eu_fr": OCRRegex(re.compile(r"fr (\d{2,3}|2[ab])[\-\s.](\d{3})[\-\s.](\d{3}) (ce|ec)(?![a-z0-9])"),
                      field=OCRField.full_text_contiguous,
                      lowercase=True,
                      processing_func=process_fr_packaging_match),
    "eu_de": OCRRegex(re.compile(r"de (bb|be|bw|by|hb|he|hh|mv|ni|nw|rp|sh|sl|sn|st|th)[\-\s.](\d{1,5})[\-\s.] ?(eg|ec)(?![a-z0-9])"),
                      field=OCRField.full_text_contiguous,
                      lowercase=True,
                      processing_func=process_de_packaging_match),
}

RECYCLING_REGEX = {
    'recycling': [
        re.compile(r"recycle", re.IGNORECASE),
    ],
    'throw_away': [
        re.compile(r"(?:throw away)|(?:jeter)", re.IGNORECASE)
    ]
}

EN_ORGANIC_REGEX_STR = [
    r'ingr[ée]dients?\sbiologiques?',
    r'ingr[ée]dients?\sbio[\s.,)]',
    r'agriculture ue/non ue biologique',
    r'agriculture bio(?:logique)?[\s.,)]',
    r'production bio(?:logique)?[\s.,)]',
]

LABELS_REGEX = {
    'en:organic': [
        OCRRegex(re.compile(r"|".join([r"(?:{})".format(x)
                                       for x in EN_ORGANIC_REGEX_STR])),
                 field=OCRField.full_text_contiguous,
                 lowercase=True),
    ],
    'xx-bio-xx': [
        # The negative lookbehind (?<![a-zA-Z]) is useful to avoid to match
        # strings if additional chars are before the label
        OCRRegex(re.compile(r"(?<![a-zA-Z])([A-Z]{2})[\-\s.](BIO|ÖKO|OKO|EKO|ØKO|ORG|ECO|Bio)[\-\s.](\d{2,3})"),
                 field=OCRField.text_annotations,
                 lowercase=False,
                 processing_func=process_eu_bio_label_code),
    ],
    'fr:ab-agriculture-biologique': [
        OCRRegex(re.compile(r"certifi[ée] ab[\s.,)]"),
                 field=OCRField.full_text_contiguous,
                 lowercase=True),
    ],
    'en:pgi': [
        OCRRegex(re.compile(
            r"indication g[ée]ographique prot[eé]g[eé]e|Indicazione geografica protetta|geschützte geografische angabe"),
                 field=OCRField.full_text_contiguous,
                 lowercase=True),
        OCRRegex(re.compile(
            r"(?<!\w)(?:IGP|BGA|PGI)(?!\w)"),
            field=OCRField.full_text_contiguous,
            lowercase=False),
    ],
    'en:pdo': [
        OCRRegex(re.compile(
            r"(?<!\w)(?:PDO|AOP|DOP)(?!\w)"),
            field=OCRField.full_text_contiguous,
            lowercase=False),
        OCRRegex(re.compile(
            r"appellation d'origine prot[eé]g[eé]e"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'fr:aoc': [
        OCRRegex(re.compile(
            r"(?<!\w)(?:AOC)(?!\w)"),
            field=OCRField.full_text_contiguous,
            lowercase=False),
        OCRRegex(re.compile(
            r"appellation d'origine contr[ôo]l[eé]e"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:nutriscore': [
        OCRRegex(re.compile(r"NUTRI-SCORE"),
                 field=OCRField.full_text,
                 lowercase=False,
                 notify=True),
    ],
    'en:eu-non-eu-agriculture': [
        OCRRegex(re.compile(r"agriculture ue\s?/\s?non\s?(?:-\s?)?ue|eu\s?/\s?non\s?(?:-\s?)?eu agriculture"),
                 field=OCRField.full_text_contiguous,
                 lowercase=True),
    ],
    'en:eu-agriculture': [
        # The negative lookafter/lookbehind forbid matching "agriculture ue/non ue"
        OCRRegex(re.compile(r"agriculture ue(?!\s?/)|(?<!-)\s?eu agriculture"),
                 field=OCRField.full_text_contiguous,
                 lowercase=True),
    ],
    'en:non-eu-agriculture': [
        OCRRegex(re.compile(r"agriculture non\s?(?:-\s?)?ue|non\s?(?:-\s?)?eu agriculture"),
                 field=OCRField.full_text_contiguous,
                 lowercase=True),
    ],
    'en:made-in-france': [
        OCRRegex(
            re.compile(r"fabriqu[ée] en france|made in france"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:made-in-spain': [
        OCRRegex(
            re.compile(r"made in spain|hecho en espa[ñn]a|geproduceerd in spanje|fabriqu[ée] en espagne|hergestellt in spanien"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:made-in-italy': [
        OCRRegex(
            re.compile(
                r"fatto in italia|made in italy|hergestellt in italien|fabriqu[ée] en italie|geproduceerd in itali[ëe]|fabricado en italia"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:made-in-belgium': [
        OCRRegex(
            re.compile(
                r"made in belgium|geproduceerd in belgi[ëe]|hecho en b[ée]lgica|fabriqu[ée] en belgique|hergestellt in belgien"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:made-in-germany': [
        OCRRegex(
            re.compile(
                r"hergestellt in deutschland|fabriqu[ée] en allemagne|geproduceerd in duitsland|hecho en alemania|made in germany"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:made-in-switzerland': [
        OCRRegex(
            re.compile(
                r"made in switzerland|geproduceerd in zwitserland|fabriqu[ée] en suisse|hecho en suiza|hergestellt in der schweiz"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:made-in-the-eu': [
        OCRRegex(
            re.compile(
                r"hergestellt in der eu|geproduceerd in de eu|fabriqu[ée] dans l'ue|hecho en la ue|made in the eu"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:australian-made': [
        OCRRegex(
            re.compile(
                r"australian made|made in australia|fabriqu[ée] en australie|geproduceerd in australi[ëe]|fabricado en australia"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:gluten-free': [
        OCRRegex(
            re.compile(r"sans gluten|gluten[- ]free|glutenvrij|senza glutine|sin gluten|glutenfrei|sem gluten|gluténmentes|bez lepku|не містить глютену|bezglutenomy|без глютена"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-preservatives': [
        OCRRegex(
            re.compile(r"senza conservanti(?! arti)|без консервантов|conserveermiddelvrij|sans conservateur(?!s? arti)|fără conservanți|no preservative|sin conservante(?!s? arti)|ohne konservierungsstoffe"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-flavors': [
        OCRRegex(
            re.compile(
                r"без ароматизаторов|senza aromi|zonder toegevoegde smaakstoffen|sans ar[ôo]mes? ajout[ée]s|sin aromas?|ohne zusatz von aromen|no flavors?"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-artificial-flavors': [
        OCRRegex(
            re.compile(
                r"без искусственных ароматизаторов|ohne künstliche aromen|sin aromas? artificiales?|vrij van kunstmatige smaakstoffen|sans ar[ôo]mes? artificiels?|no artificial flavors?"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:vegan': [
        OCRRegex(
            re.compile(
                r"(?<!\w)(?:vegan|v[ée]g[ée]talien|vegano|veganistisch)(?!\w)"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-colorings': [
        OCRRegex(
            re.compile(
                r"no colorings?|no colourants?|ohne farbstoffzusatz|sans colorants?|zonder kleurstoffen|sin colorantes?|без красителей|senza coloranti"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-additives': [
        OCRRegex(
            re.compile(
                r"zonder toevoegingen|sin aditivos(?! arti)|sans additif(?!s? arti)|ohne zusätze|no additives?"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-added-sugar': [
        OCRRegex(
            re.compile(
                r"senza zuccheri aggiunti|zonder toegevoegde suikers|sans sucres? ajout[ée]s?|sin azúcares añadidos|ohne zuckerzusatz|sem açúcares adicionados|no added sugar"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-lactose': [
        OCRRegex(
            re.compile(
                r"senza lattosio|без лактозы|bez laktozy|sans lactose|lactosevrij|no lactose|lactose[ -]free|laktózmentes|lactosefrei|sin lactosa"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:palm-oil-free': [
        OCRRegex(
            re.compile(r"без пальмового масла|senza olio di palma|ohne palmöl|sans huile de palme|sin aceite de palma|palm oil[ -]free"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:max-havelaar': [
        OCRRegex(
            re.compile(r"max havelaar"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'fr:viande-bovine-francaise': [
        OCRRegex(
            re.compile(r"viande bovine fran[çc]aise"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'fr:viande-porcine-francaise': [
        OCRRegex(
            re.compile(r"le po?rc fran[çc]ais"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:sustainable-seafood-msc': [
        OCRRegex(
            re.compile(r"www\.msc\.org"),
            field=OCRField.full_text_contiguous,
            lowercase=False),
    ],
    'en:halal': [
        OCRRegex(
            re.compile(r"(?<!\w)halal(?!\w)"),
            field=OCRField.text_annotations,
            lowercase=True),
    ],
}


def get_brand_tag(brand: str) -> str:
    return (brand.lower()
                 .replace(' ', '-')
                 .replace("'", '-'))


def brand_sort_key(item):
    """Sorting function for BRAND_DATA items.
    For the regex to work correctly, we want the longest brand names to
    appear first.
    """
    brand, _ = item

    return -len(brand), brand


def get_logo_annotation_labels() -> Dict[str, str]:
    labels: Dict[str, str] = {}

    for item in text_file_iter(settings.OCR_LOGO_ANNOTATION_LABELS_DATA_PATH):
        if '||' in item:
            logo_description, label_tag = item.split('||')
        else:
            logger.warn("'||' separator expected!")
            continue

        labels[logo_description] = label_tag

    return labels


def get_sorted_brands() -> List[Tuple[str, str]]:
    sorted_brands: Dict[str, str] = {}

    for item in text_file_iter(settings.OCR_BRANDS_DATA_PATH):
        if '||' in item:
            brand, regex_str = item.split('||')
        else:
            brand = item
            regex_str = re.escape(item.lower())

        sorted_brands[brand] = regex_str

    return sorted(sorted_brands.items(), key=brand_sort_key)


SORTED_BRANDS = get_sorted_brands()
BRAND_REGEX_STR = "|".join(r"((?<!\w){}(?!\w))".format(pattern)
                           for _, pattern in SORTED_BRANDS)
NOTIFY_BRANDS_WHITELIST: Set[str] = set(
    text_file_iter(settings.OCR_BRANDS_NOTIFY_WHITELIST_DATA_PATH))
BRAND_REGEX = OCRRegex(re.compile(BRAND_REGEX_STR),
                       field=OCRField.full_text_contiguous,
                       lowercase=True)


def generate_nutrient_regex(nutrient_names: List[str], units: List[str]):
    nutrient_names_str = '|'.join(nutrient_names)
    units_str = '|'.join(units)
    return re.compile(r"({}) ?(?:[:-] ?)?([0-9]+[,.]?[0-9]*) ?({})".format(nutrient_names_str,
                                                                           units_str))


NUTRIENT_VALUES_REGEX = {
    'energy': OCRRegex(
        generate_nutrient_regex(["[ée]nergie", "energy"], ["kj", "kcal"]),
        field=OCRField.full_text_contiguous,
        lowercase=True),
    'fat': OCRRegex(
        generate_nutrient_regex(["mati[èe]res? grasses?"], ["g"]),
        field=OCRField.full_text_contiguous,
        lowercase=True),
    'glucid': OCRRegex(
        generate_nutrient_regex(["glucides?", "glucids?"], ["g"]),
        field=OCRField.full_text_contiguous,
        lowercase=True),
    'carbohydrate': OCRRegex(
        generate_nutrient_regex(["sucres?", "carbohydrates?"], ["g"]),
        field=OCRField.full_text_contiguous,
        lowercase=True),
}

PRODUCT_WEIGHT_REGEX: Dict[str, OCRRegex] = {
    'with_mention': OCRRegex(
        re.compile(r"(poids|poids net [aà] l'emballage|poids net|poids net égoutté|masse nette|volume net total|net weight|net wt\.?|peso neto|peso liquido|netto[ -]?gewicht)\s?:?\s?([0-9]+[,.]?[0-9]*)\s?(fl oz|dle?|cle?|mge?|mle?|lbs|oz|ge?|kge?|le?)(?![a-z])"),
        field=OCRField.full_text_contiguous,
        lowercase=True,
        processing_func=functools.partial(process_product_weight, prompt=True),
        priority=1),
    'no_mention': OCRRegex(
        re.compile(r"([0-9]+[,.]?[0-9]*)\s?(dle|cle|mge|mle|ge|kge)(?![a-z])"),
        field=OCRField.full_text_contiguous,
        lowercase=True,
        processing_func=functools.partial(process_product_weight, prompt=False),
        priority=2),
}


EXPIRATION_DATE_REGEX: Dict[str, OCRRegex] = {
    'full_digits_short': OCRRegex(re.compile(r'(?<!\d)(\d{2})[-./](\d{2})[-./](\d{2})(?!\d)'),
                                  field=OCRField.full_text,
                                  lowercase=False,
                                  processing_func=functools.partial(process_full_digits_expiration_date,
                                                                    short=True)),
    'full_digits_long': OCRRegex(re.compile(r'(?<!\d)(\d{2})[-./](\d{2})[-./](\d{4})(?!\d)'),
                                 field=OCRField.full_text,
                                 lowercase=False,
                                 processing_func=functools.partial(process_full_digits_expiration_date,
                                                                   short=False)),
}

TRACES_REGEX = OCRRegex(
    re.compile(r"(?:possibilit[ée] de traces|peut contenir(?: des traces)?|traces? [ée]ventuelles? de)"),
    field=OCRField.full_text_contiguous,
    lowercase=True)


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


class Word:
    __slots__ = ('bounding_poly', 'symbols', 'text')

    def __init__(self, data: JSONType):
        self.bounding_poly = BoundingPoly(data['boundingBox'])
        self.symbols: List[Symbol] = [Symbol(s) for s in data['symbols']]
        self.text = ''.join(s.text for s in self.symbols)

    def detect_orientation(self) -> ImageOrientation:
        return self.bounding_poly.detect_orientation()


class Symbol:
    __slots__ = ('bounding_poly', 'text', 'confidence')

    def __init__(self, data: JSONType):
        self.bounding_poly = BoundingPoly(data['boundingBox'])
        self.text = data['text']
        self.confidence = data.get('confidence', None)

    def detect_orientation(self) -> ImageOrientation:
        return self.bounding_poly.detect_orientation()


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


def get_barcode_from_path(path: str) -> Optional[str]:
    barcode = ''

    for parent in pathlib.Path(path).parents:
        if parent.name.isdigit():
            barcode = parent.name + barcode
        else:
            break

    return barcode or None


def split_barcode(barcode: str) -> List[str]:
    if not barcode.isdigit():
        raise ValueError("unknown barcode format: {}".format(barcode))

    match = BARCODE_PATH_REGEX.fullmatch(barcode)

    if match:
        return [x for x in match.groups() if x]

    return [barcode]


def generate_image_url(barcode: str, image_name: str) -> str:
    splitted_barcode = split_barcode(barcode)
    path = "/{}/{}.json".format('/'.join(splitted_barcode), image_name)
    return settings.OFF_IMAGE_BASE_URL + path


def fetch_images_for_ean(ean: str):
    url = "https://world.openfoodfacts.org/api/v0/product/" \
          "{}.json?fields=images".format(ean)
    images = requests.get(url).json()
    return images


def get_json_for_image(barcode: str, image_name: str) -> \
        Optional[JSONType]:
    url = generate_image_url(barcode, image_name)
    r = requests.get(url)

    if r.status_code == 404:
        return None

    return r.json()


def get_ocr_result(data: JSONType) -> Optional[OCRResult]:
    responses = data.get('responses', [])

    if not responses:
        return None

    response = responses[0]

    if 'error' in response:
        return None

    return OCRResult(response)


def find_packager_codes(ocr_result: OCRResult) -> List[Dict]:
    results = []

    for regex_code, ocr_regex in PACKAGER_CODE.items():
        text = ocr_result.get_text(ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            if ocr_regex.processing_func is not None:
                value = ocr_regex.processing_func(match)
                results.append({
                    "raw": match.group(0),
                    "text": value,
                    "type": regex_code,
                    "notify": ocr_regex.notify,
                })

    return results


def find_nutrient_values(ocr_result: OCRResult) -> List[Dict]:
    results = []

    for regex_code, ocr_regex in NUTRIENT_VALUES_REGEX.items():
        text = ocr_result.get_text(ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            value = match.group(2).replace(',', '.')
            unit = match.group(3)
            results.append({
                "raw": match.group(0),
                "nutrient": regex_code,
                'value': value,
                'unit': unit,
                'notify': ocr_regex.notify,
            })

    return results


def find_product_weight(ocr_result: OCRResult) -> List[Dict]:
    results = []

    for type_, ocr_regex in PRODUCT_WEIGHT_REGEX.items():
        text = ocr_result.get_text(ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            if ocr_regex.processing_func is None:
                continue

            result = ocr_regex.processing_func(match)
            result['matcher_type'] = type_
            result['priority'] = ocr_regex.priority
            result['notify'] = ocr_regex.notify
            results.append(result)

    return results


def find_traces(ocr_result: OCRResult) -> List[Dict]:
    results = []

    text = ocr_result.get_text(TRACES_REGEX)

    if not text:
        return []

    for match in TRACES_REGEX.regex.finditer(text):
        raw = match.group()
        end_idx = match.end()
        captured = text[end_idx:end_idx+100]

        result = {
            'raw': raw,
            'text': captured,
            'notify': TRACES_REGEX.notify,
        }
        results.append(result)

    return results


TEMPERATURE_REGEX_STR = r"[+-]?\s*\d+\s*°?C"
TEMPERATURE_REGEX = re.compile(r"(?P<value>[+-]?\s*\d+)\s*°?(?P<unit>C)",
                               re.IGNORECASE)

STORAGE_INSTRUCTIONS_REGEX = {
    'max': re.compile(r"[aà] conserver [àa] ({0}) maximum".format(
        TEMPERATURE_REGEX_STR), re.IGNORECASE),
    'between': re.compile(r"[aà] conserver entre ({0}) et ({0})".format(
        TEMPERATURE_REGEX_STR), re.IGNORECASE),
}


def extract_temperature_information(temperature: str) -> Optional[Dict]:
    match = TEMPERATURE_REGEX.match(temperature)

    if match:
        result = {}
        value = match.group('value')
        unit = match.group('unit')

        if value:
            result['value'] = value

        if unit:
            result['unit'] = unit

        return result

    return None


def find_storage_instructions(text: str) -> List[Dict]:
    text = text.lower()

    results: List[Dict] = []

    for instruction_type, regex in STORAGE_INSTRUCTIONS_REGEX.items():
        for match in regex.finditer(text):
            if match:
                result = {
                    'text': match.group(),
                    'type': instruction_type,
                }

                if instruction_type == 'max':
                    result['max'] = extract_temperature_information(
                        match.group(1))

                elif instruction_type == 'between':
                    result['between'] = {
                        'min': extract_temperature_information(match.group(1)),
                        'max': extract_temperature_information(match.group(2)),
                    }

                results.append(result)

    return results


def find_recycling_instructions(text) -> List[Dict]:
    results = []

    for instruction_type, regex_list in RECYCLING_REGEX.items():
        for regex in regex_list:
            for match in regex.finditer(text):
                results.append({
                    'type': instruction_type,
                    'text': match.group(),
                })

    return results


LOGO_ANNOTATION_LABELS: Dict[str, str] = get_logo_annotation_labels()


def find_labels(ocr_result: OCRResult) -> List[Dict]:
    results = []

    for label_tag, regex_list in LABELS_REGEX.items():
        for ocr_regex in regex_list:
            text = ocr_result.get_text(ocr_regex)

            if not text:
                continue

            for match in ocr_regex.regex.finditer(text):
                if ocr_regex.processing_func:
                    label_value = ocr_regex.processing_func(match)
                else:
                    label_value = label_tag

                results.append({
                    'label_tag': label_value,
                    'text': match.group(),
                    'notify': ocr_regex.notify,
                })

    for logo_annotation in ocr_result.logo_annotations:
        if logo_annotation.description in LOGO_ANNOTATION_LABELS:
            label_tag = LOGO_ANNOTATION_LABELS[logo_annotation.description]

            results.append({
                'label_tag': label_tag,
                'automatic_processing': False,
                'confidence': logo_annotation.score,
            })

    return results


def find_brands(ocr_result: OCRResult) -> List[Dict]:
    results = []

    text = ocr_result.get_text(BRAND_REGEX)

    if not text:
        return []

    for match in BRAND_REGEX.regex.finditer(text):
        groups = match.groups()

        for idx, match_str in enumerate(groups):
            if match_str is not None:
                brand, _ = SORTED_BRANDS[idx]
                results.append({
                    'brand': brand,
                    'brand_tag': get_brand_tag(brand),
                    'text': match_str,
                    'notify': brand not in NOTIFY_BRANDS_WHITELIST,
                })
                break

    return results


def find_expiration_date(ocr_result: OCRResult) -> List[Dict]:
    # Parse expiration date
    #        "À consommer de préférence avant",
    results = []

    for type_, ocr_regex in EXPIRATION_DATE_REGEX.items():
        text = ocr_result.get_text(ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            raw = match.group(0)

            if not ocr_regex.processing_func:
                continue

            date = ocr_regex.processing_func(match)

            if date is None:
                continue

            if date.year > 2025 or date.year < 2015:
                continue

            value = date.strftime("%d/%m/%Y")

            results.append({
                "raw": raw,
                "text": value,
                "type": type_,
                "notify": ocr_regex.notify,
            })

    return results


def flag_image(ocr_result: OCRResult) -> List[Dict]:
    safe_search_annotation = ocr_result.get_safe_search_annotation()
    label_annotations = ocr_result.get_label_annotations()
    insights: List[Dict] = []

    if safe_search_annotation:
        for key in ('adult', 'violence'):
            value: SafeSearchAnnotationLikelihood = \
                getattr(safe_search_annotation, key)
            if value >= SafeSearchAnnotationLikelihood.VERY_LIKELY:
                insights.append({
                    'type': key,
                    'likelihood': value.name,
                })

    for label_annotation in label_annotations:
        if (label_annotation.description in ('Face', 'Head', 'Selfie') and
                label_annotation.score >= 0.8):
            insights.append({
                'type': label_annotation.description.lower(),
                'likelihood': label_annotation.score
            })
            break

    return insights


def find_image_orientation(ocr_result: OCRResult) -> List[Dict]:
    orientation_result = ocr_result.get_orientation()

    if (orientation_result is None
            or orientation_result.orientation == ImageOrientation.up):
        return []

    return [orientation_result.to_json()]


def extract_insights(ocr_result: OCRResult,
                     insight_type: str) -> List[Dict]:
    if insight_type == 'packager_code':
        return find_packager_codes(ocr_result)

    elif insight_type == 'label':
        return find_labels(ocr_result)

    elif insight_type == 'expiration_date':
        return find_expiration_date(ocr_result)

    elif insight_type == 'image_flag':
        return flag_image(ocr_result)

    elif insight_type == 'image_orientation':
        return find_image_orientation(ocr_result)

    elif insight_type == 'product_weight':
        return find_product_weight(ocr_result)

    elif insight_type == 'trace':
        return find_traces(ocr_result)

    elif insight_type == 'nutrient':
        return find_nutrient_values(ocr_result)

    elif insight_type == 'brand':
        return find_brands(ocr_result)

    else:
        raise ValueError("unknown insight type: {}".format(insight_type))


def is_barcode(text: str):
    return text.isdigit()


def get_source(image_name: str, json_path: str = None, barcode: str = None):
    if not barcode:
        barcode = get_barcode_from_path(str(json_path))

    return "/{}/{}.jpg" \
           "".format('/'.join(split_barcode(barcode)),
                     image_name)


def ocr_iter(input_str: str) -> Iterable[Tuple[Optional[str], Dict]]:
    if is_barcode(input_str):
        image_data = fetch_images_for_ean(input_str)['product']['images']

        for image_name in image_data.keys():
            if image_name.isdigit():
                print("Getting OCR for image {}".format(image_name))
                data = get_json_for_image(input_str, image_name)
                source = get_source(image_name, barcode=input_str)
                if data:
                    yield source, data

    else:
        input_path = pathlib.Path(input_str)

        if not input_path.exists():
            print("Unrecognized input: {}".format(input_path))
            return

        if input_path.is_dir():
            for json_path in input_path.glob("**/*.json"):
                with open(str(json_path), 'r') as f:
                    source = get_source(json_path.stem,
                                        json_path=str(json_path))
                    yield source, json.load(f)
        else:
            if '.json' in input_path.suffixes:
                with open(str(input_path), 'r') as f:
                    yield None, json.load(f)

            elif '.jsonl' in input_path.suffixes:
                if input_path.suffix == '.gz':
                    open_func = gzip.open
                else:
                    open_func = open

                with open_func(input_path, mode='rt') as f:
                    for line in f:
                        json_data = json.loads(line)

                        if 'content' in json_data:
                            source = json_data['source'].replace('//', '/')
                            yield source, json_data['content']


def get_ocr_from_barcode(barcode: str):
    image_data = fetch_images_for_ean(barcode)['product']['images']

    for image_name in image_data.keys():
        if image_name.isdigit():
            print("Getting OCR for image {}".format(image_name))
            data = get_json_for_image(barcode, image_name)
            return data


def get_insights_from_image(barcode: str, image_url: str, ocr_url: str) \
        -> Optional[Dict]:
    r = requests.get(ocr_url)

    if r.status_code == 404:
        return None

    r.raise_for_status()

    ocr_data: Dict = requests.get(ocr_url).json()
    ocr_result = get_ocr_result(ocr_data)
    
    if ocr_result is None:
        return None
    
    image_url_path = urlparse(image_url).path

    if image_url_path.startswith('/images/products'):
        image_url_path = image_url_path[len("/images/products"):]

    results = {}

    for insight_type in (InsightType.label.name,
                         InsightType.packager_code.name,
                         InsightType.product_weight.name,
                         InsightType.image_flag.name,
                         InsightType.expiration_date.name,
                         InsightType.brand.name):
        insights = extract_insights(ocr_result, insight_type)

        if insights:
            results[insight_type] = {
                'insights': insights,
                'barcode': barcode,
                'type': insight_type,
                'source': image_url_path,
            }

    return results
