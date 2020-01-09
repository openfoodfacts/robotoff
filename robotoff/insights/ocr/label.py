import re
from typing import Dict, List
from typing import Optional

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRRegex, OCRField, OCRResult
from robotoff.insights.ocr.flashtext import generate_keyword_processor
from robotoff.utils import text_file_iter, get_logger
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def process_eu_bio_label_code(match) -> Optional[str]:
    country = match.group(1).lower()
    bio_code = match.group(2).replace('ö', 'o').replace('ø', 'o').lower()
    id_ = match.group(3).lower()

    if country == 'de' and len(id_) != 3:
        return None

    return ("en:{}-{}-{}".format(country,
                                 bio_code,
                                 id_))


def process_es_bio_label_code(match) -> str:
    return ("en:es-eco-{}-{}".format(match.group(1),
                                     match.group(2))
            .lower())


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
        OCRRegex(re.compile(r"(?<![a-zA-Z])([A-Z]{2})[\-\s.](BIO|ÖKO|OKO|EKO|ØKO|ORG|Bio)[\-\s.](\d{2,3})"),
                 field=OCRField.text_annotations,
                 lowercase=False,
                 processing_func=process_eu_bio_label_code),
        # Spain specific regex
        OCRRegex(re.compile(r"(?<![a-zA-Z])ES[\-\s.]ECO[\-\s.](\d{3})[\-\s.]([A-Z]{2,3})"),
                 field=OCRField.text_annotations,
                 lowercase=False,
                 processing_func=process_es_bio_label_code),
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
            re.compile(r"(?<!\w)(?:sans|ni) gluten|gluten[- ]free|glutenvrij|senza glutine|sin gluten|glutenfrei|sem gluten|gluténmentes|bez lepku|не містить глютену|bezglutenomy|без глютена"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-preservatives': [
        OCRRegex(
            re.compile(r"senza conservanti(?! arti)|без консервантов|conserveermiddelvrij|(?<!\w)(?:sans|ni) conservateur(?!s? arti)|fără conservanți|no preservative|sin conservante(?!s? arti)|ohne konservierungsstoffe"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-flavors': [
        OCRRegex(
            re.compile(
                r"без ароматизаторов|senza aromi|zonder toegevoegde smaakstoffen|(?<!\w)(?:sans|ni) ar[ôo]mes? ajout[ée]s|sin aromas?|ohne zusatz von aromen|no flavors?"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-artificial-flavors': [
        OCRRegex(
            re.compile(
                r"без искусственных ароматизаторов|ohne künstliche aromen|sin aromas? artificiales?|vrij van kunstmatige smaakstoffen|(?<!\w)(?:sans|ni) ar[ôo]mes? artificiels?|no artificial flavors?"),
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
                r"no colorings?|no colourants?|ohne farbstoffzusatz|(?<!\w)(?:sans|ni) colorants?|zonder kleurstoffen|sin colorantes?|без красителей|senza coloranti"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-additives': [
        OCRRegex(
            re.compile(
                r"zonder toevoegingen|sin aditivos(?! arti)|(?<!\w)(?:sans|ni) additif(?!s? arti)|ohne zusätze|no additives?"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'en:no-added-sugar': [
        OCRRegex(
            re.compile(
                r"senza zuccheri aggiunti|zonder toegevoegde suikers|(?<!\w)(?:sans|ni) sucres? ajout[ée]s?|sin azúcares añadidos|ohne zuckerzusatz|sem açúcares adicionados|no added sugar"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
    'fr:viande-bovine-francaise': [
        OCRRegex(
            re.compile(r"viande bovine fran[çc]aise"),
            field=OCRField.full_text_contiguous,
            lowercase=True),
    ],
}


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


def generate_label_keyword_processor(labels: Optional[List[str]] = None):
    if labels is None:
        labels = text_file_iter(settings.OCR_LABEL_FLASHTEXT_DATA_PATH)

    return generate_keyword_processor(labels)


def extract_label_flashtext(processor: KeywordProcessor,
                            text: str) -> List[JSONType]:
    insights = []

    for (label_tag, label), span_start, span_end in processor.extract_keywords(
            text, span_info=True):
        match_str = text[span_start:span_end]
        insights.append({
            'label_tag': label_tag,
            'text': match_str,
            'data_source': "flashtext",
            'notify': False,
        })

    return insights


LOGO_ANNOTATION_LABELS: Dict[str, str] = get_logo_annotation_labels()
LABEL_KEYWORD_PROCESSOR_STORE = CachedStore(fetch_func=generate_label_keyword_processor,
                                            expiration_interval=None)


def find_labels(ocr_result: OCRResult) -> List[Dict]:
    insights = []

    for label_tag, regex_list in LABELS_REGEX.items():
        for ocr_regex in regex_list:
            text = ocr_result.get_text(ocr_regex)

            if not text:
                continue

            for match in ocr_regex.regex.finditer(text):
                if ocr_regex.processing_func:
                    label_value = ocr_regex.processing_func(match)

                    if label_value is None:
                        continue

                else:
                    label_value = label_tag

                insights.append({
                    'label_tag': label_value,
                    'text': match.group(),
                    'notify': ocr_regex.notify,
                    'data_source': "regex",
                })

    processor = LABEL_KEYWORD_PROCESSOR_STORE.get()
    text = ocr_result.get_full_text_contiguous(lowercase=True)

    if text is None:
        text = ocr_result.get_text_annotations(True)

    insights += extract_label_flashtext(processor, text)

    for logo_annotation in ocr_result.logo_annotations:
        if logo_annotation.description in LOGO_ANNOTATION_LABELS:
            label_tag = LOGO_ANNOTATION_LABELS[logo_annotation.description]

            insights.append({
                'label_tag': label_tag,
                'automatic_processing': False,
                'confidence': logo_annotation.score,
                'data_source': 'google-cloud-vision',
            })

    return insights
