import re
from typing import Iterable, Optional, Union

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.prediction.types import Prediction
from robotoff.types import PredictionType
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.cache import CachedStore

from .dataclass import OCRField, OCRRegex, OCRResult, get_text
from .utils import generate_keyword_processor

logger = get_logger(__name__)


def process_eu_bio_label_code(match) -> Optional[str]:
    country = match.group(1).lower()
    bio_code = match.group(2).replace("ö", "o").replace("ø", "o").lower()
    id_ = match.group(3).lower()

    if country == "de" and len(id_) != 3:
        return None

    return "en:{}-{}-{}".format(country, bio_code, id_)


def process_es_bio_label_code(match) -> str:
    return "en:es-eco-{}-{}".format(match.group(1), match.group(2)).lower()


EN_ORGANIC_REGEX_STR = [
    r"ingr[ée]dients?\sbiologiques?",
    r"ingr[ée]dients?\sbio[\s.,)]",
    r"agriculture ue/non ue biologique",
    r"agriculture bio(?:logique)?[\s.,)]",
    r"production bio(?:logique)?[\s.,)]",
]

LABELS_REGEX = {
    "en:organic": [
        OCRRegex(
            re.compile(r"|".join([r"(?:{})".format(x) for x in EN_ORGANIC_REGEX_STR])),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "xx-bio-xx": [
        # The negative lookbehind (?<![a-zA-Z]) is useful to avoid to match
        # strings if additional chars are before the label
        OCRRegex(
            re.compile(
                r"(?<![a-zA-Z])([A-Z]{2})[\-\s.](BIO|ÖKO|OKO|EKO|ØKO|ORG|Bio)[\-\s.](\d{2,3})"
            ),
            field=OCRField.text_annotations,
            lowercase=False,
            processing_func=process_eu_bio_label_code,
        ),
        # Spain specific regex
        OCRRegex(
            re.compile(r"(?<![a-zA-Z])ES[\-\s.]ECO[\-\s.](\d{3})[\-\s.]([A-Z]{2,3})"),
            field=OCRField.text_annotations,
            lowercase=False,
            processing_func=process_es_bio_label_code,
        ),
    ],
    "fr:ab-agriculture-biologique": [
        OCRRegex(
            re.compile(r"certifi[ée] ab[\s.,)]"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:pgi": [
        OCRRegex(
            re.compile(
                r"indication g[ée]ographique prot[eé]g[eé]e|Indicazione geografica protetta|geschützte geografische angabe"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
        OCRRegex(
            re.compile(r"(?<!\w)(?:IGP|BGA|PGI)(?!\w)"),
            field=OCRField.full_text_contiguous,
            lowercase=False,
        ),
    ],
    "fr:label-rouge": [
        OCRRegex(
            re.compile(r"d[ée]cret du 0?5[./]01[./]07"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
        OCRRegex(
            re.compile(r"(?<!\w)homologation(?: n°?)? ?la ?\d{2}\/\d{2}(?!\w)"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:pdo": [
        OCRRegex(
            re.compile(r"(?<!\w)(?:PDO|AOP|DOP)(?!\w)"),
            field=OCRField.full_text_contiguous,
            lowercase=False,
        ),
        OCRRegex(
            re.compile(r"appellation d'origine prot[eé]g[eé]e"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "fr:aoc": [
        OCRRegex(
            re.compile(r"(?<!\w)(?:AOC)(?!\w)"),
            field=OCRField.full_text_contiguous,
            lowercase=False,
        ),
    ],
    "en:nutriscore": [
        OCRRegex(
            re.compile(r"NUTRI-SCORE"),
            field=OCRField.full_text,
            lowercase=False,
        ),
    ],
    "en:eu-non-eu-agriculture": [
        OCRRegex(
            re.compile(
                r"agriculture ue\s?/\s?non\s?(?:-\s?)?ue|eu\s?/\s?non\s?(?:-\s?)?eu agriculture"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:eu-agriculture": [
        # The negative lookafter/lookbehind forbid matching "agriculture ue/non ue"
        OCRRegex(
            re.compile(r"agriculture ue(?!\s?/)|(?<!-)\s?eu agriculture"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:non-eu-agriculture": [
        OCRRegex(
            re.compile(r"agriculture non\s?(?:-\s?)?ue|non\s?(?:-\s?)?eu agriculture"),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:no-preservatives": [
        OCRRegex(
            re.compile(
                r"senza conservanti(?! arti)|без консервантов|conserveermiddelvrij|(?<!\w)(?:sans|ni) conservateur(?!s? arti)|fără conservanți|no preservative|sin conservante(?!s? arti)|ohne konservierungsstoffe"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:no-flavors": [
        OCRRegex(
            re.compile(
                r"без ароматизаторов|senza aromi|zonder toegevoegde smaakstoffen|(?<!\w)(?:sans|ni) ar[ôo]mes? ajout[ée]s|sin aromas?|ohne zusatz von aromen|no flavors?"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:no-artificial-flavors": [
        OCRRegex(
            re.compile(
                r"без искусственных ароматизаторов|ohne künstliche aromen|sin aromas? artificiales?|vrij van kunstmatige smaakstoffen|(?<!\w)(?:sans|ni) ar[ôo]mes? artificiels?|no artificial flavors?"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:no-colorings": [
        OCRRegex(
            re.compile(
                r"no colorings?|no colourants?|ohne farbstoffzusatz|(?<!\w)(?:sans|ni) colorants?|zonder kleurstoffen|sin colorantes?|без красителей|senza coloranti"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
    "en:no-additives": [
        OCRRegex(
            re.compile(
                r"zonder toevoegingen|sin aditivos(?! arti)|(?<!\w)(?:sans|ni) additif(?!s? arti)|ohne zusätze|no additives?"
            ),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        ),
    ],
}


def get_logo_annotation_labels() -> dict[str, str]:
    labels: dict[str, str] = {}

    for item in text_file_iter(settings.OCR_LOGO_ANNOTATION_LABELS_DATA_PATH):
        if "||" in item:
            logo_description, label_tag = item.split("||")
        else:
            logger.warning("'||' separator expected!")
            continue

        labels[logo_description] = label_tag

    return labels


def generate_label_keyword_processor(labels: Optional[Iterable[str]] = None):
    if labels is None:
        labels = text_file_iter(settings.OCR_LABEL_FLASHTEXT_DATA_PATH)

    return generate_keyword_processor(labels)


def extract_label_flashtext(processor: KeywordProcessor, text: str) -> list[Prediction]:
    predictions = []

    for (label_tag, _), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        match_str = text[span_start:span_end]
        predictions.append(
            Prediction(
                type=PredictionType.label,
                value_tag=label_tag,
                automatic_processing=False,
                predictor="flashtext",
                data={"text": match_str, "notify": False},
            )
        )

    return predictions


LOGO_ANNOTATION_LABELS: dict[str, str] = get_logo_annotation_labels()
LABEL_KEYWORD_PROCESSOR_STORE = CachedStore(
    fetch_func=generate_label_keyword_processor, expiration_interval=None
)


def find_labels(content: Union[OCRResult, str]) -> list[Prediction]:
    predictions = []

    for label_tag, regex_list in LABELS_REGEX.items():
        for ocr_regex in regex_list:
            text = get_text(content, ocr_regex)

            if not text:
                continue

            for match in ocr_regex.regex.finditer(text):
                if ocr_regex.processing_func:
                    label_value = ocr_regex.processing_func(match)

                    if label_value is None:
                        continue

                else:
                    label_value = label_tag

                predictions.append(
                    Prediction(
                        type=PredictionType.label,
                        value_tag=label_value,
                        predictor="regex",
                        data={"text": match.group(), "notify": ocr_regex.notify},
                    )
                )

    processor = LABEL_KEYWORD_PROCESSOR_STORE.get()

    text = get_text(content)
    predictions += extract_label_flashtext(processor, text)

    if isinstance(content, OCRResult):
        for logo_annotation in content.logo_annotations:
            if logo_annotation.description in LOGO_ANNOTATION_LABELS:
                label_tag = LOGO_ANNOTATION_LABELS[logo_annotation.description]

                predictions.append(
                    Prediction(
                        type=PredictionType.label,
                        value_tag=label_tag,
                        automatic_processing=False,
                        predictor="google-cloud-vision",
                        data={"confidence": logo_annotation.score},
                    )
                )

    return predictions
