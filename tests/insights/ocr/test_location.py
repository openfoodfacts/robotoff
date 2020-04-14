from flashtext import KeywordProcessor
import pytest

from robotoff import settings
from robotoff.insights.ocr.dataclass import OCRResult
from robotoff.insights.ocr.location import (
    City,
    AddressExtractor,
    load_cities_fr,
)


module = "robotoff.insights.ocr.location"


def test_load_cities_fr(mocker):
    m_gzip_open = mocker.patch(f"{module}.gzip.open")
    m_json_load = mocker.patch(
        f"{module}.json.load",
        return_value=[
            {
                "fields": {
                    "nom_de_la_commune": "PARIS",
                    "code_postal": "75000",
                    "coordonnees_gps": [48.866667, 2.333333],
                },
            },
            {"fields": {"nom_de_la_commune": "POYA", "code_postal": "98827"}},
        ],
    )

    res = load_cities_fr()

    m_gzip_open.assert_called_once_with(settings.OCR_CITIES_FR_PATH, "rb")
    m_json_load.assert_called_once_with(m_gzip_open.return_value.__enter__.return_value)
    assert res == [
        City("paris", "75000", (48.866667, 2.333333)),
        City("poya", "98827", None),
    ]


def test_cities_fr_dataset():
    cities_fr = load_cities_fr()

    assert all(isinstance(item, City) for item in cities_fr)
    assert len(set(cities_fr)) == len(cities_fr)
    assert all(isinstance(c.name, str) and len(c.name) > 0 for c in cities_fr)
    assert all(
        isinstance(c.postal_code, str) and len(c.postal_code) == 5 for c in cities_fr
    )
    non_null_coords = [c.coordinates for c in cities_fr if c.coordinates is not None]
    assert all(
        isinstance(c, tuple)
        and len(c) == 2
        and isinstance(c[0], float)
        and isinstance(c[1], float)
        for c in non_null_coords
    )


@pytest.fixture
def cities():
    return [City("paris", "75000", (48.866667, 2.333333)), City("poya", "98827", None)]


def test_address_extractor_init(mocker, cities):
    m_add_keyword = mocker.patch.object(KeywordProcessor, "add_keyword")

    ae = AddressExtractor(cities)

    assert isinstance(ae.cities_processor, KeywordProcessor)
    assert m_add_keyword.call_args_list == [
        mocker.call("paris", cities[0]), mocker.call("poya", cities[1])
    ]


def test_address_extractor_get_text(mocker):
    # OCRResult instance with a full_text_annotation
    m_ocr_result = mocker.Mock(
        get_full_text=mocker.Mock(return_value="full text à-é'$"),
        text_annotations=[mocker.Mock(text="TEXT É'-č"), "yolo"],
    )

    assert AddressExtractor.get_text(m_ocr_result) == "full text a e $"
    m_ocr_result.get_full_text.assert_called_once_with(lowercase=True)

    # OCRResult instance without a full_text_annotation
    m_ocr_result = mocker.Mock(
        get_full_text=mocker.Mock(return_value=None),
        text_annotations=[mocker.Mock(text="TEXT É'-č"), "yolo"],
    )

    assert AddressExtractor.get_text(m_ocr_result) == "text e  c"
    m_ocr_result.get_full_text.assert_called_once_with(lowercase=True)


def test_address_extractor_find_city_names():
    c1 = City("abc", "12345", None)
    c2 = City("def g", "12345", None)
    ae = AddressExtractor([c1, c2])

    assert ae.find_city_names("without city") == []
    assert ae.find_city_names("with def and g") == []
    assert ae.find_city_names("with the abc city") == [(c1, 9, 12)]
    assert ae.find_city_names("with the def g city") == [(c2, 9, 14)]
    assert ae.find_city_names("with def g and abc cities") == [
        (c2, 5, 10), (c1, 15, 18)]


def test_address_extractor_find_nearby_postal_code():
    """WIP"""
