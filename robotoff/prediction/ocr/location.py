import dataclasses
import gzip
import json
import re
from pathlib import Path
from typing import BinaryIO, Iterable, Optional, Union

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.prediction.types import Prediction
from robotoff.types import PredictionType
from robotoff.utils import get_logger
from robotoff.utils.cache import CachedStore
from robotoff.utils.text import strip_accents_ascii

from .dataclass import OCRResult


@dataclasses.dataclass(frozen=True)
class City:
    """A city, storing its name, postal code and GPS coordinates."""

    name: str
    """The city name, lower case, no accents, with special characters replaced with
    spaces."""
    postal_code: str
    """The city's postal code. The format depends on the country."""
    coordinates: Optional[tuple[float, float]]
    """The GPS coordinates of the city as a tuple of two floats, or None."""


def load_cities_fr(source: Union[Path, BinaryIO, None] = None) -> set[City]:
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


class AddressExtractor:
    """Text processor to extract French addresses based on city name and postal code.

    The main entry point is the `extract_addresses()` method. An `OCRResult` is
    searched for addresses in the following way:

    * The text is prepared by taking it lower case, removing accents, and replacing
      the characters ' and - with " " (space), as city names must follow this format.
    * City names are searched for in the text.
    * For each city name found, its corresponding postal code is searched for in the
      surrounding text, at a maximum distance of `postal_code_search_distance`.
    * If the postal code is found, the match is added to the list of returned
      addresses, along with an extract of the text surrounding the address,
      at a maximum distance of `text_extract_distance`.

    Args:
        cities (iterable of City): Set of cities to search for.
        postal_code_search_distance (int, optional, default 10): Maximum distance
            from a city name to search for a postal code.
        text_extract_distance (int, optional, default 30): Amount of text surrounding a
            detected address to extract for returning.
    """

    def __init__(
        self,
        cities: Iterable[City],
        postal_code_search_distance: int = 10,
        text_extract_distance: int = 30,
    ):
        self.cities = cities
        self.postal_code_search_distance = postal_code_search_distance
        self.text_extract_distance = text_extract_distance

        self.cities_processor = KeywordProcessor()
        for city in self.cities:
            self.cities_processor.add_keyword(city.name, city)

    def extract_addresses(self, content: Union[str, OCRResult]) -> list[Prediction]:
        """Extract addresses from the given OCR result.

        Args:
            content (OCRResult or str): a string or the OCR result to process.

        Returns:
            list of Prediction: List of addresses extracted from the text. Each entry
            is a dictionary with the items: country_code (always "fr"), city_name,
            postal_code and text_extract.
        """
        if isinstance(content, OCRResult):
            text = self.get_text(content)
        else:
            text = content

        text = self.normalize_text(text)
        city_matches = self.find_city_names(text)

        locations = []
        for city, city_start, city_end in city_matches:
            pc_match = self.find_nearby_postal_code(text, city, city_start, city_end)
            if pc_match is None:
                continue

            pc, pc_start, pc_end = pc_match
            address_start = min(city_start, pc_start) - self.text_extract_distance
            address_end = max(city_end, pc_end) + self.text_extract_distance
            text_extract = text[max(0, address_start) : min(len(text), address_end)]

            locations.append(
                Prediction(
                    type=PredictionType.location,
                    data={
                        "country_code": "fr",
                        "city_name": city.name,
                        "postal_code": city.postal_code,
                        "text_extract": text_extract,
                    },
                )
            )

        return locations

    @staticmethod
    def get_text(ocr_result: OCRResult) -> str:
        """Extract text from the OCR result and prepare it.

        Args:
            ocr_result (OCRResult): The OCR result to process.

        Returns:
            str: The text extracted and prepared.
        """
        text = ocr_result.get_full_text()
        if text is None:
            # Using `OCRResult.text_annotations` directly instead of
            # `OCRResult.get_text_annotations()` because the latter contains
            # the text duplicated
            text = ocr_result.text_annotations[0].text
        return text

    @staticmethod
    def normalize_text(text: str) -> str:
        text = text.lower()
        text = strip_accents_ascii(text)
        return text.replace("'", " ").replace("-", " ")

    def find_city_names(self, text: str) -> list[tuple[City, int, int]]:
        """Find all cities from the search set in the text.

        Args:
            text (str): Text to search city names in.

        Returns:
            list of (City, int, int): The list of `City`s which name was found in the
            text, with the start and end indices of their names locations in the
            text. Empty list if none found.
        """
        return self.cities_processor.extract_keywords(text, span_info=True)

    def find_nearby_postal_code(
        self, text: str, city: City, city_start: int, city_end: int
    ) -> Optional[tuple[str, int, int]]:
        """Search for a city's postal code close to its name in the text.

        The postal code is searched at a maximum distance of
        `postal_code_search_distance` from the city name.

        Assumes digit-only postal code, allows non-digit directly next to it. For
        example, for the city "paris" with postal code "75000", "75000 paris" and
        "fr75000 paris" will match.

        Args:
            text (str): The OCR result text.
            city (City): The `City` for which to search the postal code.
            city_start (int): Start index of the city name match in `text`.
            city_end (int): End index of the city name match in `text`.

        Returns:
            (str, int, int) or None: If the `City`'s postal code was found close to
            the city name match, it is returned along with its start and end indices
            in the text. If it was not found, returns None.
        """
        if not city.postal_code.isdigit():
            logger = get_logger(
                "{}.{}".format(self.__module__, self.__class__.__name__)
            )
            logger.error("postal code contains non-digit characters: %s", city)
            return None
        pattern = r"(?:[^0-9]|^)({})(?:[^0-9]|$)".format(city.postal_code)

        sub_start = max(0, city_start - self.postal_code_search_distance)
        sub_end = min(len(text), city_end + self.postal_code_search_distance)
        sub_text = text[sub_start:sub_end]

        match = re.search(pattern, sub_text)
        if match is None:
            return None
        else:
            return match.group(1), sub_start + match.start(1), sub_start + match.end(1)


ADDRESS_EXTRACTOR_STORE = CachedStore(
    lambda: AddressExtractor(load_cities_fr()), expiration_interval=None
)


def find_locations(content: Union[OCRResult, str]) -> list[Prediction]:
    """Find location predictions in the text content.

    See :class:`.AddressExtractor`.

    Args:
        content (OCRResult or str): The content to be searched for locations.

    Returns:
        list of Prediction: See :meth:`.AddressExtractor.extract_addresses`.
    """
    location_extractor: AddressExtractor = ADDRESS_EXTRACTOR_STORE.get()
    return location_extractor.extract_addresses(content)
