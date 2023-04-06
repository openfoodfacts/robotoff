import functools
import re
from typing import Iterable, Optional, Union

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.types import Prediction, PredictionType
from robotoff.utils import get_logger, text_file_iter

from .dataclass import OCRField, OCRRegex, OCRResult, get_match_bounding_box, get_text
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
            re.compile(
                r"|".join([r"(?:{})".format(x) for x in EN_ORGANIC_REGEX_STR]), re.I
            ),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "xx-bio-xx": [
        # The negative lookbehind (?<![a-zA-Z]) is useful to avoid to match
        # strings if additional chars are before the label
        OCRRegex(
            re.compile(
                r"(?<![a-zA-Z])([A-Z]{2})[\-\s.](BIO|ÖKO|OKO|EKO|ØKO|ORG|Bio)[\-\s.](\d{2,3})"
            ),
            field=OCRField.full_text,
            processing_func=process_eu_bio_label_code,
        ),
        # Spain specific regex
        OCRRegex(
            re.compile(r"(?<![a-zA-Z])ES[\-\s.]ECO[\-\s.](\d{3})[\-\s.]([A-Z]{2,3})"),
            field=OCRField.full_text,
            processing_func=process_es_bio_label_code,
        ),
    ],
    "fr:ab-agriculture-biologique": [
        OCRRegex(
            re.compile(r"certifi[ée] ab[\s.,)]", re.I),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:pgi": [
        OCRRegex(
            re.compile(
                r"indication g[ée]ographique prot[eé]g[eé]e|Indicazione geografica protetta|geschützte geografische angabe",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
        ),
        OCRRegex(
            re.compile(r"(?<!\w)(?:IGP|BGA|PGI)(?!\w)"),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "fr:label-rouge": [
        OCRRegex(
            re.compile(r"d[ée]cret du 0?5[./]01[./]07", re.I),
            field=OCRField.full_text_contiguous,
        ),
        OCRRegex(
            re.compile(r"(?<!\w)homologation(?: n°?)? ?la ?\d{2}\/\d{2}(?!\w)", re.I),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:pdo": [
        OCRRegex(
            re.compile(r"(?<!\w)(?:PDO|AOP|DOP)(?!\w)"),
            field=OCRField.full_text_contiguous,
        ),
        OCRRegex(
            re.compile(r"appellation d'origine prot[eé]g[eé]e", re.I),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "fr:aoc": [
        OCRRegex(
            re.compile(r"(?<!\w)(?:AOC)(?!\w)"), field=OCRField.full_text_contiguous
        ),
    ],
    "en:nutriscore": [
        OCRRegex(re.compile(r"NUTRI-SCORE"), field=OCRField.full_text),
    ],
    "en:eu-non-eu-agriculture": [
        OCRRegex(
            re.compile(
                r"agriculture ue\s?/\s?non\s?(?:-\s?)?ue|eu\s?/\s?non\s?(?:-\s?)?eu agriculture",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:eu-agriculture": [
        # The negative lookafter/lookbehind forbid matching "agriculture ue/non ue"
        OCRRegex(
            re.compile(r"agriculture ue(?!\s?/)|(?<!-)\s?eu agriculture", re.I),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:non-eu-agriculture": [
        OCRRegex(
            re.compile(
                r"agriculture non\s?(?:-\s?)?ue|non\s?(?:-\s?)?eu agriculture", re.I
            ),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:no-preservatives": [
        OCRRegex(
            re.compile(
                r"senza conservanti(?! arti)|без консервантов|conserveermiddelvrij|(?<!\w)(?:sans|ni) conservateur(?!s? arti)|fără conservanți|no preservative|sin conservante(?!s? arti)|ohne konservierungsstoffe",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:no-flavors": [
        OCRRegex(
            re.compile(
                r"без ароматизаторов|senza aromi|zonder toegevoegde smaakstoffen|(?<!\w)(?:sans|ni) ar[ôo]mes? ajout[ée]s|sin aromas?|ohne zusatz von aromen|no flavors?",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:no-artificial-flavors": [
        OCRRegex(
            re.compile(
                r"без искусственных ароматизаторов|ohne künstliche aromen|sin aromas? artificiales?|vrij van kunstmatige smaakstoffen|(?<!\w)(?:sans|ni) ar[ôo]mes? artificiels?|no artificial flavors?",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:no-colorings": [
        OCRRegex(
            re.compile(
                r"no colorings?|no colourants?|ohne farbstoffzusatz|(?<!\w)(?:sans|ni) colorants?|zonder kleurstoffen|sin colorantes?|без красителей|senza coloranti",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
        ),
    ],
    "en:no-additives": [
        OCRRegex(
            re.compile(
                r"zonder toevoegingen|sin aditivos(?! arti)|(?<!\w)(?:sans|ni) additif(?!s? arti)|ohne zusätze|no additives?",
                re.I,
            ),
            field=OCRField.full_text_contiguous,
        ),
    ],
}


@functools.cache
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


@functools.cache
def generate_label_keyword_processor(labels: Optional[Iterable[str]] = None):
    if labels is None:
        labels = text_file_iter(settings.OCR_LABEL_FLASHTEXT_DATA_PATH)

    return generate_keyword_processor(labels)


def extract_label_flashtext(
    processor: KeywordProcessor, content: Union[OCRResult, str]
) -> list[Prediction]:
    predictions = []

    text = get_text(content)
    for (label_tag, _), span_start, span_end in processor.extract_keywords(
        text, span_info=True
    ):
        match_str = text[span_start:span_end]
        data = {"text": match_str, "notify": False}

        if (
            bounding_box := get_match_bounding_box(content, span_start, span_end)
        ) is not None:
            data["bounding_box_absolute"] = bounding_box

        predictions.append(
            Prediction(
                type=PredictionType.label,
                value_tag=label_tag,
                automatic_processing=False,
                predictor="flashtext",
                data=data,
            )
        )

    return predictions


def find_labels(content: Union[OCRResult, str]) -> list[Prediction]:
    predictions = []
    logo_annotation_labels = get_logo_annotation_labels()

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

                data = {"text": match.group(), "notify": ocr_regex.notify}
                if (
                    bounding_box := get_match_bounding_box(
                        content, match.start(), match.end()
                    )
                ) is not None:
                    data["bounding_box_absolute"] = bounding_box

                predictions.append(
                    Prediction(
                        type=PredictionType.label,
                        value_tag=label_value,
                        predictor="regex",
                        data=data,
                    )
                )

    processor = generate_label_keyword_processor()
    predictions += extract_label_flashtext(processor, content)

    if isinstance(content, OCRResult):
        for logo_annotation in content.logo_annotations:
            if logo_annotation.description in logo_annotation_labels:
                label_tag = logo_annotation_labels[logo_annotation.description]

                predictions.append(
                    Prediction(
                        type=PredictionType.label,
                        value_tag=label_tag,
                        automatic_processing=False,
                        predictor="google-cloud-vision",
                        confidence=logo_annotation.score,
                    )
                )

    return predictions
