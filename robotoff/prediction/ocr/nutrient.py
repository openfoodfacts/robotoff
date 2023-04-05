import re
from typing import Union

from robotoff.types import JSONType, Prediction, PredictionType

from .dataclass import OCRField, OCRRegex, OCRResult, get_match_bounding_box, get_text

EXTRACTOR_VERSION = "2"


NutrientMentionType = tuple[str, list[str]]

NUTRIENT_MENTION: dict[str, list[NutrientMentionType]] = {
    "energy": [
        ("[ée]nergie", ["fr", "de"]),
        ("valeurs? [ée]nerg[ée]tiques?", ["fr"]),
        ("energy", ["en"]),
        ("calories", ["fr", "en"]),
        ("energia", ["es", "it", "pt"]),
        ("valor energ[ée]tico", ["es"]),
    ],
    "saturated_fat": [
        ("mati[èe]res? grasses? satur[ée]s?", ["fr"]),
        ("acides? gras satur[ée]s?", ["fr"]),
        ("dont satur[ée]s?", ["fr"]),
        ("acidi grassi saturi", ["it"]),
        ("saturated fat", ["en"]),
        ("of which saturates", ["en"]),
        ("verzadigde vetzuren", ["nl"]),
        ("waarvan verzadigde", ["nl"]),
        ("gesättigte fettsäuren", ["de"]),
        ("[aá]cidos grasos saturados", ["es"]),
    ],
    "trans_fat": [("mati[èe]res? grasses? trans", ["fr"]), ("trans fat", ["en"])],
    "fat": [
        ("mati[èe]res? grasses?", ["fr"]),
        ("graisses?", ["fr"]),
        ("lipides?", ["fr"]),
        ("total fat", ["en"]),
        ("vetten", ["nl"]),
        ("fett", ["de"]),
        ("grasas", ["es"]),
        ("grassi", ["it"]),
        ("l[íi]pidos", ["es"]),
    ],
    "sugar": [
        ("sucres?", ["fr"]),
        ("sugars?", ["en"]),
        ("zuccheri", ["it"]),
        ("suikers?", ["nl"]),
        ("zucker", ["de"]),
        ("az[úu]cares", ["es"]),
    ],
    "carbohydrate": [
        ("total carbohydrate", ["en"]),
        ("glucids?", ["fr"]),
        ("glucides?", ["en"]),
        ("carboidrati", ["it"]),
        ("koolhydraten", ["nl"]),
        ("koolhydraat", ["nl"]),
        ("kohlenhydrate", ["de"]),
        ("hidratos de carbono", ["es"]),
    ],
    "protein": [
        ("prot[ée]ines?", ["fr"]),
        ("protein", ["en"]),
        ("eiwitten", ["nl"]),
        ("eiweiß", ["de"]),
        ("prote[íi]nas", ["es"]),
    ],
    "salt": [
        ("sel", ["fr"]),
        ("salt", ["en"]),
        ("zout", ["nl"]),
        ("salz", ["de"]),
        ("sale", ["it"]),
        ("sal", ["es"]),
    ],
    "fiber": [
        ("fibres?", ["en", "fr", "it"]),
        ("fibers?", ["en"]),
        ("fibres? alimentaires?", ["fr"]),
        ("(?:voedings)?vezels?", ["nl"]),
        ("ballaststoffe", ["de"]),
        ("fibra(?: alimentaria)?", ["es"]),
    ],
    "nutrition_values": [
        ("informations? nutritionnelles?(?: moyennes?)?", ["fr"]),
        ("valeurs? nutritionnelles?(?: moyennes?)?", ["fr"]),
        ("analyse moyenne pour", ["fr"]),
        ("valeurs? nutritives?", ["fr"]),
        ("valeurs? moyennes?", ["fr"]),
        ("nutrition facts?", ["en"]),
        ("average nutritional values?", ["en"]),
        ("valori nutrizionali medi", ["it"]),
        ("gemiddelde waarden per", ["nl"]),
    ],
}


NUTRIENT_UNITS: dict[str, list[str]] = {
    "energy": ["kj", "kcal"],
    "saturated_fat": ["g"],
    "trans_fat": ["g"],
    "fat": ["g"],
    "sugar": ["g"],
    "carbohydrate": ["g"],
    "protein": ["g"],
    "salt": ["g"],
    "fiber": ["g"],
}


def generate_nutrient_regex(
    nutrient_mentions: list[NutrientMentionType], units: list[str]
):
    nutrient_names = [x[0] for x in nutrient_mentions]
    nutrient_names_str = "|".join(nutrient_names)
    units_str = "|".join(units)
    return re.compile(
        r"(?<!\w)({}) ?(?:[:-] ?)?([0-9]+[,.]?[0-9]*) ?({})(?!\w)".format(
            nutrient_names_str, units_str
        ),
        re.I,
    )


def generate_nutrient_mention_regex(nutrient_mentions: list[NutrientMentionType]):
    sub_re = "|".join(
        r"(?P<{}>{})".format("{}_{}".format("_".join(lang), i), name)
        for i, (name, lang) in enumerate(nutrient_mentions)
    )
    return re.compile(r"(?<!\w){}(?!\w)".format(sub_re), re.I)


NUTRIENT_VALUES_REGEX = {
    nutrient: OCRRegex(
        generate_nutrient_regex(NUTRIENT_MENTION[nutrient], units),
        field=OCRField.full_text_contiguous,
    )
    for nutrient, units in NUTRIENT_UNITS.items()
}

NUTRIENT_MENTIONS_REGEX: dict[str, OCRRegex] = {
    nutrient: OCRRegex(
        generate_nutrient_mention_regex(NUTRIENT_MENTION[nutrient]),
        field=OCRField.full_text_contiguous,
    )
    for nutrient in NUTRIENT_MENTION
}


def find_nutrient_values(content: Union[OCRResult, str]) -> list[Prediction]:
    nutrients: JSONType = {}

    for regex_code, ocr_regex in NUTRIENT_VALUES_REGEX.items():
        text = get_text(content, ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            value = match.group(2).replace(",", ".")
            unit = match.group(3)
            nutrients.setdefault(regex_code, [])
            nutrients[regex_code].append(
                {
                    "raw": match.group(0),
                    "nutrient": regex_code,
                    "value": value,
                    "unit": unit,
                }
            )

    if not nutrients:
        return []

    return [
        Prediction(
            type=PredictionType.nutrient,
            data={"nutrients": nutrients, "version": EXTRACTOR_VERSION},
        )
    ]


def find_nutrient_mentions(content: Union[OCRResult, str]) -> list[Prediction]:
    nutrients: JSONType = {}

    for regex_code, ocr_regex in NUTRIENT_MENTIONS_REGEX.items():
        text = get_text(content, ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            nutrients.setdefault(regex_code, [])
            group_dict = {k: v for k, v in match.groupdict().items() if v is not None}

            languages: list[str] = []
            if group_dict:
                languages_raw = list(group_dict.keys())[0]
                languages = languages_raw.rsplit("_", maxsplit=1)[0].split("_")

            nutrient_data = {
                "raw": match.group(0),
                "span": list(match.span()),
                "languages": languages,
            }
            if (
                bounding_box := get_match_bounding_box(
                    content, match.start(), match.end()
                )
            ) is not None:
                nutrient_data["bounding_box_absolute"] = bounding_box

            nutrients[regex_code].append(nutrient_data)

    if not nutrients:
        return []

    return [
        Prediction(
            type=PredictionType.nutrient_mention,
            data={"mentions": nutrients, "version": EXTRACTOR_VERSION},
        )
    ]
