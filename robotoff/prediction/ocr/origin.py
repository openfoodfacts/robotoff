import collections
import json
import re
from typing import Any, Dict, List, Union

from robotoff import settings
from robotoff.prediction.types import Prediction, PredictionType

from .dataclass import OCRField, OCRRegex, OCRResult, get_text

EXTRACTOR_VERSION = "1"

# TODO: check that commit suggested are still in place


class OriginParser:
    LARGE_ORIGIN = "large origin"  # large origin means several countries, or an unknown country outside of the local area.
    # (ex: "quinoa comes from outside the E.U", "quinoa has several origins")
    UNKNOW_ORIGIN = "unknow origin"
    ALL_INGREDIENTS = "all ingredients"

    def __init__(self) -> None:
        self.initialized = False

    def initialize(self):
        self.INGREDIENTS = {}
        INGREDIENTS = json.load(open(settings.TAXONOMY_CATEGORY_PATH, "r"))

        # French ----------------
        INGREDIENTS_SYNONYMS_FR = [
            ingredient["synonyms"]["fr"]
            for ingredient in INGREDIENTS.values()
            if "synonyms" in ingredient and "fr" in ingredient["synonyms"]
        ]
        INGREDIENTS_FR = [
            synonym for synonyms in  INGREDIENTS_SYNONYMS_FR for synonym in synonyms
        ]
        GENERAL_WORDS_FR = [
            "ingredients?",
            "[ée]lements?",
            "composition",
            "production",
            "mati[èe]res? premi[èe]res?",
        ]
        INGREDIENTS_FR.extend(
            [
                "ingr[ée]dients?",
                "[ée]l[ée]ments?",
                "composition",
                "production",
                "mati[èe]res? premi[èe]res?",
            ]
        )
        INGREDIENTS_FR_JOINED = "|".join(INGREDIENTS_FR)

        self.COUNTRIES_IN_ALL_LANGS = {}
        COUNTRIES_IN_ALL_LANGS = json.load(
            open(settings.OCR_TAXONOMY_COUNTRIES_PATH, "r")
        )

        COUNTRIES_FR = [
            country["name"]["fr"]
            for country in COUNTRIES_IN_ALL_LANGS.values()
            if "name" in country and "fr" in country["name"]
        ]
        COUNTRIES_FR.extend([r"Union Europ[ée]enne", r"E\.?U\.?", r"U\.?E\.?"])
        COUNTRIES_FR_JOINED = "|".join(COUNTRIES_FR)

        COUNTRIES_NATIONALITY_ADJECTIVES_FR = [
            country["nationalities"]["fr"]
            for country in COUNTRIES_IN_ALL_LANGS.values()
            if "nationalities" in country and "fr" in country["nationalities"]
        ]
        COUNTRIES_NATIONALITY_ADJECTIVES_FR.append("européen(?:ne)?s?")

        COUNTRIES_ADJECTIVES_FR_JOINED = "|".join(COUNTRIES_NATIONALITY_ADJECTIVES_FR)
        VERBS_FR_JOINED = "|".join(
            [
                "fabriqu[ée]e?s?",
                "pr[ée]par[ée]?e?s?",
                "faite?s?",
                "produite?s?",
                "cuisin[ée]e?s?",
                "cr[ée][ée]e?s?",
                "cultiv[ée]e?s?",
                "[ée]lev[ée]e?s?",
                "provient",
                "proviennent",
                "vient",
                "viennent",
                "a",
                "ont",
            ]
        )

        COUNTRY_ADJECTIVE_FR_TO_COUNTRY_NAME_FR = {
            COUNTRIES_IN_ALL_LANGS[country_id]["nationalities"]["fr"]: country_id
            for country_id in COUNTRIES_IN_ALL_LANGS.keys()
            if country_id in COUNTRIES_IN_ALL_LANGS
            and "nationalities" in COUNTRIES_IN_ALL_LANGS[country_id]
            and "fr" in COUNTRIES_IN_ALL_LANGS[country_id]["nationalities"]
        }

        OUTSIDE_WORDS_FR = ["hors", "en dehors"]

        # This regex tries to match all possible sentences we could see on a product that tell something
        # about the origin of the product, or any of its ingredients.
        FR_ORIGIN_REGEX = rf'''\b(?<!\w) #avoid matching empty string
        (?P<ingredients>(?:(?:{INGREDIENTS_FR_JOINED}) #group "ingredients" (Optional) ->the ingredients, one string for all ingredients (may be "Quinoa and Wheat").
        # Use extract_ingredients_from_match_string() to split the ingredients into a list of strings
        \s? #space
        
        (?:et\s|,\s?)?\s?)*)?\s? #link words
        
        (?:100%)?\s? #allows matching sentences like "100% french"
        
        # "negation" (Optional) (boolean) -> if this group is not None, then the sentence is negative,
        # and the specified ingredient don't comes from the specified country, i.e this ingredient has a LARGE_ORIGIN
        (?P<negation>n'|ne)\s?     

        (?:est|sont|a|ont)?\s? #link words (is, are)
        
        (?:{VERBS_FR_JOINED})?\s? #verbs
        
        (?:pas|plus)?\s? # link words (when there is a negation)

        # "in_or_outside" (Optional) -> a word, that tell if the product is product in the specified country or outside. Can be :
        #     - inside the specified country : "dans" "depuis" "en"
        #     - outside the specified country : "hors" "en dehors"
        #     if it is None, you can safely think of it as "inside the specified country"
        (?P<in_or_outside>dans|depuis|hors|en\sdehors|en)?\s? 

        (?:de\sfabrication|d'|de\sla|de\sl'\s|de|du)?\s? #link words

        # if none of the three groups below is found in the regex, then ignore the match, it does'nt tell anything about the origin
        # - "country" (Optional) -> the place from which the product comes as a noun
        # - "country_adj" (Optional) -> the place from which the product comes as an adjective
        # - "large_origin" (Optional) -> (boolean) the place from which the product comes is large, or its ingredients come from several different countries
        (?:(?P<country>{COUNTRIES_FR_JOINED})
        |(?P<country_adj>{COUNTRIES_ADJECTIVES_FR_JOINED})
        |(?P<large_origin>(?:divers(?:es)?|diff[ée]rent(?:es)?|autres|un\sautre|plusieurs\sautres|plusieurs)\s(?:pays|[ée]tats?|r[ée]gions?|continents?|origines?)))\b(?!\w)'''
        FR_ORIGIN_OCR_REGEX = OCRRegex(
            re.compile(FR_ORIGIN_REGEX, flags=re.IGNORECASE|re.VERBOSE),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        )

        # English -----------------------

        INGREDIENTS_SYNONYMS_EN = [
            ingredient["synonyms"]["en"]
            for ingredient in INGREDIENTS.values()
            if "synonyms" in ingredient and "en" in ingredient["synonyms"]
        ]
        INGREDIENTS_EN = [
            synonym for synonyms in  INGREDIENTS_SYNONYMS_EN for synonym in synonyms
        ]  # flatten the array
        GENERAL_WORDS_EN = ["ingredients?", "elements?", "composition", "production"]
        INGREDIENTS_EN.extend(GENERAL_WORDS_EN)
        INGREDIENTS_EN_JOINED = "|".join(INGREDIENTS_EN)

        COUNTRIES_EN = [
            coutry["name"]["en"]
            for coutry in COUNTRIES_IN_ALL_LANGS.values()
            if "name" in coutry and "en" in coutry["name"]
        ]
        COUNTRIES_EN.extend([r"European Union", r"E\.?U\.?"])
        COUNTRIES_EN_JOINED = "|".join(COUNTRIES_EN)

        COUNTRIES_NATIONALITY_ADJECTIVES_EN = [
            country["nationalities"]["en"]
            for country in COUNTRIES_IN_ALL_LANGS.values()
            if "nationalities" in country and "en" in country["nationalities"]
        ]
        COUNTRIES_NATIONALITY_ADJECTIVES_EN.append("european")

        COUNTRIES_ADJECTIVES_EN_JOINED = "|".join(COUNTRIES_NATIONALITY_ADJECTIVES_EN)
        VERBS_EN_JOINED = "|".join(
            [
                "made",
                "prepared",
                "produced",
                "created",
                "grown",
                "farmed",
                "cooked",
                "raised",
                "comes?",
                "ha(?:s|ve)",
            ]
        )

        COUNTRY_ADJECTIVE_EN_TO_COUNTRY_NAME_EN = {
            COUNTRIES_IN_ALL_LANGS[country_id]["nationalities"]["en"]: country_id
            for country_id in COUNTRIES_IN_ALL_LANGS.keys()
            if country_id in COUNTRIES_IN_ALL_LANGS
            and "nationalities" in COUNTRIES_IN_ALL_LANGS[country_id]
            and "en" in COUNTRIES_IN_ALL_LANGS[country_id]["nationalities"]
        }

        OUTSIDE_WORDS_EN = ["outside"]

        # Same regex in english. See the french one to know about groups. 
        # I"m not bilingual in english, so if you find missing terms, missing ways of telling the
        # origin of an ingredient, feel free to add it. 
        # You can also add other langages. Make a regex in this language and add it to self.EVERY_REGEX_BY_LANG.
        # also add the general words (like "diverse origin", "different places") to self.GENERAL_WORDS_BY_LANG
        EN_ORIGIN_REGEX = rf"\b(?<!\w)(?P<country_adj>{COUNTRIES_ADJECTIVES_EN_JOINED})?\s?(?P<ingredients>(?:(?:{INGREDIENTS_EN_JOINED})\s?(?:and\s|,\s?)?\s?)*)?\s?(?:100%)?\s?(?:is|are|has|have)?\s?(?P<negation>'nt|not)?\s?(?:{VERBS_EN_JOINED})?\s?(?P<in_or_outside>inside|in|from|outside)?\s?(?:of)?\s(?:the)?\s?(?P<country>{COUNTRIES_EN_JOINED})\s?(?P<large_origin>(?:several\sother|several|different?|other|an\sother)\s(?:countries|states?|regions?|continents?|origins?))?\b(?!\w)"
        EN_ORIGIN_OCR_REGEX = OCRRegex(
            re.compile(EN_ORIGIN_REGEX, flags=re.IGNORECASE|re.VERBOSE),
            field=OCRField.full_text_contiguous,
            lowercase=True,
        )

        self.INGREDIENTS_ID = collections.defaultdict(dict)
        for ingredient_id, ingredient in INGREDIENTS.items():
            for lang, name in ingredient["name"].items():
                self.INGREDIENTS_ID[lang][name] = ingredient_id

        self.EVERY_REGEX_BY_LANG: Dict[str, OCRRegex] = {
            "fr": FR_ORIGIN_OCR_REGEX,
            "en": EN_ORIGIN_OCR_REGEX,
        }
        self.GENERAL_WORDS_BY_LANG: Dict[str, List[str]] = {
            "fr": GENERAL_WORDS_FR,
            "en": GENERAL_WORDS_EN,
        }
        self.COUNTRY_ADJECTIVE_TO_COUNTRY_NAME_BY_LANG = {
            "fr": COUNTRY_ADJECTIVE_FR_TO_COUNTRY_NAME_FR,
            "en": COUNTRY_ADJECTIVE_EN_TO_COUNTRY_NAME_EN,
        }

        self.OUTSIDE_WORDS_BY_LANG = {"fr": OUTSIDE_WORDS_FR, "en": OUTSIDE_WORDS_EN}

    def find_origin(self, content: Union[OCRResult, str]) -> List[Prediction]:
        """
        Returns a list of Prediction, each prediction as a "data" field that contains a "ingredients_origins"
        field. Each "ingredients_origins" dict has three fields :
        "origin" -> the country, a region from which specified ingredients comes.
        "same_for_all_ingredients" -> a boolean, if True then all the ingredient of the product have the
        specified origin, and the third field "concerned_ingredient" is None
        "concerned_ingredient" -> if "same_for_all_ingredients" is False, then this field is a list of the
        ingredient that comes from the regions specified in "origin".
        """
        if not self.initialized:
            self.initialize()

        ingredients_origins: Dict[str, Dict[str, Any]] = {}
        for lang, regex in self.EVERY_REGEX_BY_LANG.items():
            text = get_text(content, regex)

            if not text:
                return []

            for match in regex.regex.finditer(text):
                origin = self.extract_origin_from_match(match, lang)
                
                if not origin or origin == OriginParser.UNKNOW_ORIGIN:
                    continue

                if not origin in ingredients_origins:
                    ingredients_origins[origin] = {
                        "origin": origin,
                        "same_for_all_ingredients": True,  # True unless group "ingredients" matched
                        "concerned_ingredients": None,
                    }

                if self.check_if_general_word_in_ingredients(
                    self.GENERAL_WORDS_BY_LANG[lang], match.group("ingredients")
                ):
                    continue

                if not match.group("ingredients"):
                    continue

                ingredients = self.extract_ingredients_from_match_string(
                    match.group("ingredients"), lang
                )
                if ingredients is not None:
                    ingredients_origins[origin]["same_for_all_ingredients"] = False
                    ingredients_origins[origin]["concerned_ingredients"] = []
                    for ingredient in ingredients:
                        ingredients_origins[origin]["concerned_ingredients"].append(
                            ingredient
                        )

        return [
            Prediction(
                type=PredictionType.nutrient,
                data={"ingredients_origins": origin, "version": EXTRACTOR_VERSION},
            )
            for origin in ingredients_origins.values()
        ]

    def check_if_general_word_in_ingredients(
        self, general_words_regex: List[str], ingredients: str
    ):
        """
        Utility function for checking if one of the general words like 'elements' or 'ingredients' is
        present in the list of ingredients returned by extract_ingredients_from_match_string
        """
        return any(
            re.search(reg, ingredients) is not None for reg in general_words_regex
        )

    def extract_origin_from_match(self, origin_match, lang: str) -> str:
        if (
            origin_match.group("in_or_outside") is not None
            and origin_match.group("in_or_outside") in self.OUTSIDE_WORDS_BY_LANG[lang]
        ):
            return (
                OriginParser.LARGE_ORIGIN
            )  # the sentence tells that the product is made outside a zone,
            # so the only thing we can extract is that it has a large origin
        elif origin_match.group("negation") is not None:
            return (
                OriginParser.LARGE_ORIGIN
            )  # the sentence tells that the product is not made in the specified zone,
            # so the only thing we can extract is that it has a large origin
        elif origin_match.group("country") is not None:

            def standardize(s):
                return " ".join(
                    (word[0].upper() + word[1:].lower() for word in s.split(" "))
                )

            standardized_name = standardize(origin_match.group("country"))
            try:
                return next(  # find the translation in english of the specified country name
                    country_id
                    for country_id, country_content in self.COUNTRIES_IN_ALL_LANGS.items()
                    if country_content["name"][lang] == standardized_name
                )
            except StopIteration:  # impossible, if the regex matched with the group country, the country with this name exists
                return standardized_name
        elif (
            origin_match.group("country_adj") is not None
            and origin_match.group("country")
            in self.COUNTRY_ADJECTIVE_TO_COUNTRY_NAME_BY_LANG[lang]
        ):
            return self.COUNTRY_ADJECTIVE_TO_COUNTRY_NAME_BY_LANG[lang][
                origin_match.group("country_adj").lower()
            ]
        elif origin_match.group("large_origin") is not None:
            return OriginParser.LARGE_ORIGIN
        else:
            return OriginParser.UNKNOW_ORIGIN

    def extract_ingredients_from_match_string(
        self, ingredients_text: str, lang
    ) -> List[str]:
        """
        Utility function that splits the regex's matched group "ingredient" into a list of ingredients.
        the regex matches with sentence with several ingredients, like 'quinoa and rice are made in France'
        It match the whole "quinoa and rice " string, and this function splits each ingredients.
        """
        splitted = ingredients_text.split()

        def standardize_ingredient(s):
            return s[0].upper() + s[1:].lower()

        standardized = map(standardize_ingredient, splitted)

        def to_id(s):
            return self.INGREDIENTS_ID[lang].get(s, s)

        ingredients_ids = map(to_id, standardized)
        return list(ingredients_ids)


origin_parser = OriginParser()
