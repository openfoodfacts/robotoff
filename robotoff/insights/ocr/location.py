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


logger = get_logger(__name__)


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
        coords = city_data.get("coordonnees_gps")
        if coords is not None:
            coords = tuple(coords)
        cities.append(
            City(
                city_data["nom_de_la_commune"].lower(), city_data["code_postal"], coords
            )
        )

    # Remove duplicates
    return set(cities)


class AddressExtractor:
    """Suited for digit-only postal codes."""
    # TODO:
    #   * use city name and postal code distance
    #   * handle stop word in city names? (l, la...)
    def __init__(
        self,
        cities: Iterable[City],
        postal_code_search_distance: int = 10,
        text_extract_distance: int = 30
    ):
        self.cities = cities
        self.postal_code_search_distance = postal_code_search_distance
        self.text_extract_distance = text_extract_distance

        self.cities_processor = KeywordProcessor()
        for city in self.cities:
            self.cities_processor.add_keyword(city.name, city)

    def extract_addresses(self, ocr_result: OCRResult) -> List[JSONType]:
        text = self.get_text(ocr_result)
        cities = self.find_city_names(text)

        locations = []
        for city, *city_span in cities:
            pc_match = self.find_nearby_postal_code(text, city, city_span)
            if pc_match is None:
                continue

            pc, pc_start, pc_end = pc_match
            address_start = min(city_span[0], pc_start) - self.text_extract_distance
            address_end = max(city_span[1], pc_end) + self.text_extract_distance
            text_extract = text[max(0, address_start):min(len(text), address_end)]

            locations.append(
                {
                    "country_code": "fr",
                    "city_name": city.name,
                    "postal_code": city.postal_code,
                    "text_extract": text_extract,
                }
            )

        return locations

    @staticmethod
    def get_text(ocr_result: OCRResult) -> str:
        text = ocr_result.get_full_text(lowercase=True)
        if text is None:
            # Using `OCRResult.text_annotations` directly instead of
            # `OCRResult.get_text_annotations()` because the latter contains
            # the text duplicated
            text = ocr_result.text_annotations[0].text.lower()
        text = strip_accents_ascii(text)
        text = text.replace("'", " ").replace("-", " ")
        return text

    def find_city_names(self, text: str) -> List[Tuple[City, int, int]]:
        return self.cities_processor.extract_keywords(text, span_info=True)

    def find_nearby_postal_code(self, text: str, city: City, span: Tuple[int, int]):
        """Assumes digit-only postal code, allows non-digit directly next to it."""
        if not city.postal_code.isdigit():
            raise ValueError(f"postal code contains non-digit characters: {city}")
        pattern = r"(?:[^0-9]|^)({})(?:[^0-9]|$)".format(city.postal_code)

        sub_start = max(0, span[0] - self.postal_code_search_distance)
        sub_end = min(len(text), span[1] + self.postal_code_search_distance)
        sub_text = text[sub_start:sub_end]

        match = re.search(pattern, sub_text)
        if match is None:
            return None
        else:
            return match.group(1), sub_start + match.start(1), sub_start + match.end(1)


ADDRESS_EXTRACTOR_STORE = CachedStore(
    lambda: AddressExtractor(load_cities_fr()), expiration_interval=None
)


def find_locations(content: Union[OCRResult, str]) -> List[JSONType]:
    location_extractor: AddressExtractor = ADDRESS_EXTRACTOR_STORE.get()
    return location_extractor.extract_addresses(content)
