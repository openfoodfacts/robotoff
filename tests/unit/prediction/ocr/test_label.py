import pytest

from robotoff.prediction.ocr.label import LABELS_REGEX, find_labels

XX_BIO_XX_OCR_REGEX = LABELS_REGEX["xx-bio-xx"][0]
ES_BIO_OCR_REGEX = LABELS_REGEX["xx-bio-xx"][1]


@pytest.mark.parametrize(
    "input_str,is_match,output",
    [
        ("ES-ECO-001-AN", True, "en:es-eco-001-an"),
        ("ES-ECO-001", False, None),
        ("ES-ECO-001-", False, None),
        ("FR-BIO-01", False, None),
    ],
)
def test_es_ocr_regex(input_str: str, is_match: bool, output: str | None):
    regex = ES_BIO_OCR_REGEX.regex
    match = regex.match(input_str)
    assert (match is not None) == is_match

    if is_match:
        assert ES_BIO_OCR_REGEX.processing_func(match) == output  # type: ignore


@pytest.mark.parametrize(
    "text,value_tags",
    [
        ("certifié ab.", ["fr:ab-agriculture-biologique"]),
        ("Homologation n° LA 21/88", ["fr:label-rouge"]),
        ("homologation LA 42/05", ["fr:label-rouge"]),
        ("Homologation n°LA19/05", ["fr:label-rouge"]),
        ("Homologation n°LA 02/91", ["fr:label-rouge"]),
        ("Nouveau calcul", ["en:nutriscore-v2"]),
        ("NOUVEAU CALCUL", ["en:nutriscore-v2"]),
        ("nouveau calcul", ["en:nutriscore-v2"]),
        ("New calculation", ["en:nutriscore-v2"]),
        ("Neue Berechnung", ["en:nutriscore-v2"]),
        ("Nuevo cálculo", ["en:nutriscore-v2"]),
        ("Nuevo calculo", ["en:nutriscore-v2"]),
        ("Nuovo calcolo", ["en:nutriscore-v2"]),
        ("Nieuwe berekening", ["en:nutriscore-v2"]),
        ("Novo cálculo", ["en:nutriscore-v2"]),
        ("Ny beregning", ["en:nutriscore-v2"]),
        ("Uusi laskenta", ["en:nutriscore-v2"]),
        ("Novi izračun", ["en:nutriscore-v2"]),
        ("Ново изчисление", ["en:nutriscore-v2"]),
        ("NUTRI-SCORE Nouveau calcul", ["en:nutriscore", "en:nutriscore-v2"]),
    ],
)
def test_find_labels(text: str, value_tags: list[str]):
    insights = find_labels(text)
    detected_value_tags = set(i.value_tag for i in insights)
    assert detected_value_tags == set(value_tags)
