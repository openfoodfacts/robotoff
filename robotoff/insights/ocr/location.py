import dataclasses
import gzip
import json
from pathlib import Path
import re
from typing import Union, List, Optional, Tuple, BinaryIO, Set, Iterable

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRResult
from robotoff.utils import get_logger
from robotoff.utils.cache import CachedStore
from robotoff.utils.text import strip_accents_ascii
from robotoff.utils.types import JSONType


@dataclasses.dataclass(frozen=True)
class City:
    """A city, storing its name, postal code and GPS coordinates."""

    name: str
    """The city name, lower case, no accents, with special characters replaced with 
    spaces."""
    postal_code: str
    """The city's postal code. The format depends on the country."""
    coordinates: Optional[Tuple[float, float]]
    """The GPS coordinates of the city as a tuple of two floats, or None."""


def load_cities_fr(source: Union[Path, BinaryIO, None] = None) -> Set[City]:
    """Load French cities dataset.

    French cities are taken from the La Poste hexasmal dataset:
    https://datanova.legroupe.laposte.fr/explore/dataset/laposte_hexasmal/. The
    source file must be a gzipped-JSON.

    The returned set of cities can contain multiple items with the same name: multiple
    cities can exist with the same name but a different postal code.

    Also, the original dataset may contain multiple items with are not unique with
    regard to the :class:`City` class' attributes: there are additional fields in the
    original dataset which are ignored here. These duplicates are removed.

    Args:
        source (Path or BinaryIO or None, optional, default None): Path to the dataset
            file or open binary stream. If None, the dataset file contained in the
            repo will be used.

    Returns:
        set of City: List of all French cities as `City` objects.

    Raises:
        ValueError: if a postal code is not a valid French postal code (5 digits).
    """
    # JSON file contains a lot of repeated data. An alternative could be to use the
    # CSV file.
    if source is None:
        source = settings.OCR_CITIES_FR_PATH

    # Load JSON content
    with gzip.open(source, "rb") as cities_file:
        json_data = json.load(cities_file)

    # Create City objects
    cities = []
    for item in json_data:
        city_data = item["fields"]
        name = city_data["nom_de_la_commune"].lower()
        postal_code = city_data["code_postal"]
        if not len(postal_code) == 5 or not postal_code.isdigit():
            raise ValueError(
                "{!r}, invalid FR postal code for city {!r}, must be 5-digits "
                "string".format(postal_code, name)
            )
        coords = city_data.get("coordonnees_gps")
        if coords is not None:
            coords = tuple(coords)
        cities.append(City(name, postal_code, coords))

    # Remove duplicates
    return set(cities)


def load_city_blacklist_fr(source: Union[Path, BinaryIO, None] = None) -> List[str]:
    if source is None:
        source = settings.OCR_CITY_BLACKLIST_FR_PATH

    with open(source, "rt") as blacklist_file:
        return blacklist_file.readlines()


class AddressExtractor:
    """Text processor to extract French addresses based on city name and postal code.

    The main entry point is the `extract_addresses()` method. An `OCRResult` is
    searched for addresses in the following way:

    * The text is prepared by taking it lower case, removing accents, and replacing
      the characters ' and - with " " (space), as city names must follow this format.
    * City names are searched for in the text.
    * For each city name found:
      * A postal code is searched for in the surrounding text, at a maximum distance
        of `postal_code_search_distance`.
      * Marker words are searched for at the left of the city name, at a maximum
        distance of `marker_search_distance`.

    Args:
        cities (iterable of City): Set of cities to search for.
        postal_code_search_distance (int, optional, default 10): Maximum distance
            from a city name to search for a postal code.
        text_extract_distance (int, optional, default 30): Amount of text surrounding a
            detected address to extract for returning.
    """

    marker_words = ["transforme", "elabore", "produit"]

    def __init__(
        self,
        cities: Iterable[City],
        city_blacklist: Iterable[str],
        postal_code_search_distance: int = 10,
        marker_search_distance: int = 60,
        text_extract_distance: int = 30,
    ):
        self.cities = list(cities)
        self.city_blacklist = list(city_blacklist)
        self.postal_code_search_distance = postal_code_search_distance
        self.marker_search_distance = marker_search_distance
        self.text_extract_distance = text_extract_distance

        self.cities_processor = KeywordProcessor()
        for city in self.cities:
            self.cities_processor.add_keyword(city.name, city)

        self.marker_processor = KeywordProcessor()
        self.marker_processor.add_keywords_from_list(self.marker_words)

    def extract_addresses(self, ocr_result: OCRResult) -> List[JSONType]:
        """Extract addresses from the given OCR result.

        Args:
            ocr_result (OCRResult): The OCR result to process.

        Returns:
            list of JSONType: List of addresses extracted from the text. Each entry
            is a dictionary with the items: country_code (always "fr"), city_name,
            postal_code and text_extract.
        """
        text = self.get_text(ocr_result)
        city_matches = self.find_city_names(text)
        language = self.get_language(ocr_result)

        locations = []
        for city, blacklisted, city_start, city_end in city_matches:
            location = {
                "language": language,
                "country_code": "fr",
                "city": {
                    "name": city.name,
                    "blacklisted": blacklisted,
                },
                "postal_code": None,
                "markers": None,
            }
            location_start = city_start
            location_end = city_end

            pc_match = self.find_nearby_postal_code(text, city, city_start, city_end)
            if pc_match is not None:
                match_level, pc, pc_start, pc_end = pc_match
                location["postal_code"] = {
                    "match_level": match_level, "value": pc
                }
                location_start = min(location_start, pc_start)
                location_end = max(location_end, pc_end)

            markers = self.find_nearby_markers(text, city_start, city_end)
            if markers:
                location["markers"] = [m[0] for m in markers]
                location_start = min(location_start, *[m[1] for m in markers])
                location_end = max(location_end, *[m[2] for m in markers])

            text_extract = text[
                max(0, location_start - self.text_extract_distance)
                : min(len(text), location_end + self.text_extract_distance)
            ]
            location["text_extract"] = text_extract
            locations.append(location)

        return locations

    @staticmethod
    def get_text(ocr_result: OCRResult) -> str:
        """Extract text from the OCR result and prepare it.

        Args:
            ocr_result (OCRResult): The OCR result to process.

        Returns:
            str: The text extracted and prepared.
        """
        text = ocr_result.get_full_text(lowercase=True)
        if text is None:
            # Using `OCRResult.text_annotations` directly instead of
            # `OCRResult.get_text_annotations()` because the latter contains
            # the text duplicated
            text = ocr_result.text_annotations[0].text.lower()
        text = strip_accents_ascii(text)
        text = text.replace("'", " ").replace("-", " ")
        return text

    @staticmethod
    def get_language(ocr_result: OCRResult) -> Optional[str]:
        """Return the most probable language for the text of the `OCRResult`.

        Args:
            ocr_result (OCRResult): The OCR result to process.

        Returns:
            str or None: The 2-letter language code of the most probable language
            detected for the text, or None if none could be detected.
        """
        languages = ocr_result.get_languages()
        if languages is None:
            return None
        languages.pop("words")
        sorted_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        most_frequent = sorted_languages[0][0]
        return None if most_frequent == "null" else most_frequent

    def find_city_names(self, text: str) -> List[Tuple[City, bool, int, int]]:
        """Find all cities from the search set in the text.

        Args:
            text (str): Text to search city names in.

        Returns:
            list of (City, bool, int, int): City matches found in the text, as a list
            of tuples with items:

            * `City` object for which the name was found in the text
            * blacklist indicator: True if the city name is blacklisted, False otherwise
            * start index of the city name in the text
            * end index of the ciy name in the text

            Empty list if no city name found.
        """
        city_matches = self.cities_processor.extract_keywords(text, span_info=True)
        return [
            (m[0], m[0].name in self.city_blacklist,) + m[1:]
            for m in city_matches
        ]

    def find_nearby_postal_code(
        self, text: str, city: City, city_start: int, city_end: int
    ) -> Optional[Tuple[str, str, int, int]]:
        """Search for a city's postal code close to its name in the text.

        The postal code is searched at a maximum distance (including the postal code
        itself) of `postal_code_search_distance` from the city name.

        Assumes digit-only postal code. Allows a non-digit directly next to it: for
        the city "paris" with postal code "75000", "75000 paris" and "fr75000\n
        paris" will match, "750006" will not. Allows a space between the department part
        (first 2 digits) and the rest of the postal code: "75000 paris" and "75 000
        paris" will match.

        A postal code is searched for with multiple levels of specificity, in that
        order:

        * exact: an exact postal code, e.g. 75000
        * department: a postal code with only the department part (first 2 digits)
          matching the city one's, e.g. 75xxx
        * general: a sequence of 5 digits, e.g. xxxxx

        Only the most specific match level is returned.

        Args:
            text (str): The OCR result text.
            city (City): The `City` for which to search the postal code.
            city_start (int): Start index of the city name match in `text`.
            city_end (int): End index of the city name match in `text`.

        Returns:
            (str, str, int, int) or None: If a postal code was found close to the city
            name, a tuple with the following items:

            * match level: "exact", "department" or "general"
            * postal code match value, normalized (no spaces)
            * start index of the postal code match in the text
            * end index of the postal code match in the text

            If no postal code match was found, returns None.
        """
        if not city.postal_code.isdigit():
            logger = get_logger(
                "{}.{}".format(self.__module__, self.__class__.__name__)
            )
            logger.error("postal code contains non-digit characters: %s", city)
            return None

        # Postal codes can be of the form "12345" or "12 345"
        pc_patterns = [
            ("exact", "{}[ ]?{}".format(city.postal_code[:2], city.postal_code[2:])),
            ("department", "{}[ ]?[0-9]{{3}}".format(city.postal_code[:2])),
            ("general", "[0-9]{2}[ ]?[0-9]{3}"),
        ]
        pattern = r"(?:[^0-9]|^)({})(?:[^0-9]|$)"

        sub_start = max(0, city_start - self.postal_code_search_distance)
        sub_end = min(len(text), city_end + self.postal_code_search_distance)
        sub_text = text[sub_start:sub_end]

        for match_level, pc_pattern in pc_patterns:
            match = re.search(pattern.format(pc_pattern), sub_text)
            if match is None:
                continue
            return (
                match_level,
                match.group(1).replace(" ", ""),
                sub_start + match.start(1),
                sub_start + match.end(1),
            )
        return None

    def find_nearby_markers(
        self, text: str, city_start: int, city_end: int
    ) -> List[Tuple[str, int, int]]:
        """Search for marker words near a city name.

        Search only on the left, as always follows a pattern like "élaboré à quimper".

        Args:
            text (str): The OCR result text.
            city_start (int): Start index of the city name match.
            city_end (int): End index of the city name.

        Returns:
            list of (str, int, int): Marker words found close to the city name,
            as a list of tuples with the marker word, and its start and end indices
            in the text.
        """
        sub_start = max(0, city_start - self.marker_search_distance)
        sub_text = text[sub_start:city_start]
        matches = self.marker_processor.extract_keywords(sub_text, span_info=True)
        return [(m[0], sub_start + m[1], sub_start + m[2]) for m in matches]


ADDRESS_EXTRACTOR_STORE = CachedStore(
    lambda: AddressExtractor(load_cities_fr(), load_city_blacklist_fr()),
    expiration_interval=None,
)


def find_locations(content: Union[OCRResult, str]) -> List[JSONType]:
    """Find location insights in the text content.

    See :class:`.AddressExtractor`.

    Args:
        content (OCRResult or str): The content to be searched for locations.

    Returns:
        list of JSONType: See :meth:`.AddressExtractor.extract_addresses`.
    """
    location_extractor: AddressExtractor = ADDRESS_EXTRACTOR_STORE.get()
    return location_extractor.extract_addresses(content)
