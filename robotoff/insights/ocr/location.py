import dataclasses
import gzip
import json
from pathlib import Path
import re
from typing import Union, List, Dict, Optional, Tuple, Sequence, BinaryIO

from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRResult
from robotoff.utils import get_logger
from robotoff.utils.cache import CachedStore
from robotoff.utils.text import strip_accents_ascii


logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class City:
    """A city, storing its name, postal code and GPS coordinates."""

    name: str
    postal_code: str
    coordinates: Optional[Tuple[float, float]]


def load_cities_fr(source: Union[Path, BinaryIO, None] = None) -> List[City]:
    """Load French cities dataset.

    French cities are taken from the La Poste hexasmal dataset:
    https://datanova.legroupe.laposte.fr/explore/dataset/laposte_hexasmal/. The
    source file must be a gzipped-JSON.

    The returned list of cities can contain multiple items with the same name: multiple
    cities can exist with the same name but a different postal code.

    Also, the original dataset may contain multiple items with are not unique with
    regard to the :class:`City` class' attributes: there are additional fields in the
    original dataset which are ignored here. These duplicates are removed.

    Args:
        source (Path or BinaryIO or None, optional, default None): Path to the dataset
            file or open binary stream. If None, the dataset file contained in the
            repo will be used.

    Returns:
        list of City: List of all French cities as `City` objects.
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
    return list(set(cities))


class AddressExtractor:
    # TODO:
    #   * use city name and postal code distance
    #   * handle stop word in city names? (l, la...)
    def __init__(self, cities: Sequence[City]):
        self.cities = cities
        self.cities_processor = KeywordProcessor()
        for city in self.cities:
            self.cities_processor.add_keyword(city.name, city)

    def extract_location(self, ocr_result: OCRResult):
        text = self.prepare_text(ocr_result.text_annotations_str_lower)
        cities = self.find_city_names(text)

        surround_distance = 30
        full_cities = []
        addresses = []
        for city, *span in cities:
            nearby_code = self.find_nearby_postal_code(text, city, span)
            if nearby_code is not None:
                full_cities.append((nearby_code, (city.name, *span)))
                address_start = min(span[0], nearby_code[1]) - surround_distance
                address_end = max(span[1], nearby_code[2]) + surround_distance
                addresses.append(
                    text[max(0, address_start):min(len(text), address_end)]
                )

        return {"cities": [(c[0].name, *c[1:]) for c in cities],
                "full_cities": full_cities,
                "addresses": addresses
                }

    def prepare_text(self, text_annotations_str_lower: str) -> str:
        text = text_annotations_str_lower
        text = text[:text.find("||")]  # Keep only full description
        text = strip_accents_ascii(text)
        text = text.replace("'", " ").replace("-", " ")
        return text

    def find_city_names(self, text: str) -> List[Tuple[City, int, int]]:
        return self.cities_processor.extract_keywords(text, span_info=True)

    def find_nearby_postal_code(self, text: str, city: City, span: Tuple[int, int]):
        max_distance = 10
        pattern = r"(?:[^0-9]|^)({})(?:[^0-9]|$)".format(city.postal_code)
        sub_start = max(0, span[0] - max_distance)
        sub_end = min(len(text), span[1] + max_distance)
        sub_text = text[sub_start:sub_end]
        match = re.search(pattern, sub_text)
        if match is None:
            return None
        else:
            return match.group(), sub_start + match.start(), sub_start + match.end()


ADDRESS_EXTRACTOR_STORE = CachedStore(
    lambda: AddressExtractor(load_cities_fr()), expiration_interval=None
)


def find_locations(content: Union[OCRResult, str]) -> List[Dict]:
    location_extractor = ADDRESS_EXTRACTOR_STORE.get()
    return [location_extractor.extract_location(content)]
