import pytest
from flashtext import KeywordProcessor

from robotoff import settings
from robotoff.prediction.ocr.location import (
    AddressExtractor,
    City,
    find_locations,
    load_cities_fr,
)

module = "robotoff.prediction.ocr.location"


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
    assert res == {
        City("paris", "75000", (48.866667, 2.333333)),
        City("poya", "98827", None),
    }

    # Error with postal code with bad length
    mocker.resetall()
    m_json_load.return_value = [
        {"fields": {"nom_de_la_commune": "YOLO", "code_postal": "123"}},
    ]

    with pytest.raises(
        ValueError, match="'123', invalid FR postal code for city 'yolo'"
    ):
        load_cities_fr()

    m_gzip_open.assert_called_once_with(settings.OCR_CITIES_FR_PATH, "rb")
    m_json_load.assert_called_once_with(m_gzip_open.return_value.__enter__.return_value)

    # Error with non-digit postal code
    mocker.resetall()
    m_json_load.return_value = [
        {"fields": {"nom_de_la_commune": "YOLO", "code_postal": "12A42"}},
    ]

    with pytest.raises(
        ValueError, match="'12A42', invalid FR postal code for city 'yolo'"
    ):
        load_cities_fr()

    m_gzip_open.assert_called_once_with(settings.OCR_CITIES_FR_PATH, "rb")
    m_json_load.assert_called_once_with(m_gzip_open.return_value.__enter__.return_value)


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
        mocker.call("paris", cities[0]),
        mocker.call("poya", cities[1]),
    ]


def test_address_extractor_get_text(mocker):
    # OCRResult instance with a full_text_annotation
    m_ocr_result = mocker.Mock(
        get_full_text=mocker.Mock(return_value="full text l'île-àÉ$"),
        text_annotations=[mocker.Mock(text="TEXT É'-č"), "yolo"],
    )

    assert AddressExtractor.get_text(m_ocr_result) == "full text l'île-àÉ$"
    m_ocr_result.get_full_text.assert_called_once_with()

    # OCRResult instance without a full_text_annotation
    m_ocr_result = mocker.Mock(
        get_full_text=mocker.Mock(return_value=None),
        text_annotations=[mocker.Mock(text="TEXT É'-č"), "yolo"],
    )

    assert AddressExtractor.get_text(m_ocr_result) == "TEXT É'-č"
    m_ocr_result.get_full_text.assert_called_once_with()


@pytest.mark.parametrize(
    "text,output",
    [("full text l'île-àÉ$", "full text l ile ae$"), ("TEXT É'-č", "text e  c")],
)
def test_address_extractor_normalize(text: str, output: str):
    assert AddressExtractor.normalize_text(text) == output


def test_address_extractor_find_city_names():
    c1 = City("abc", "12345", None)
    c2 = City("def g", "12345", None)
    ae = AddressExtractor([c1, c2])

    assert ae.find_city_names("without city") == []
    assert ae.find_city_names("with def and g") == []
    assert ae.find_city_names("with the abc city") == [(c1, 9, 12)]
    assert ae.find_city_names("with the def g city") == [(c2, 9, 14)]
    assert ae.find_city_names("with def g and abc cities") == [
        (c2, 5, 10),
        (c1, 15, 18),
    ]


def test_address_extractor_find_nearby_postal_code(mocker):
    c = City("abc", "12345", None)
    ae = AddressExtractor([c], postal_code_search_distance=8)

    assert ae.find_nearby_postal_code("blah abc 12345", c, 5, 8) == ("12345", 9, 14)
    assert ae.find_nearby_postal_code("abc fr12345-", c, 0, 3) == ("12345", 6, 11)
    assert ae.find_nearby_postal_code("12345- abc fr", c, 7, 10) == ("12345", 0, 5)
    assert ae.find_nearby_postal_code("blah abc 123456", c, 5, 8) is None
    assert ae.find_nearby_postal_code("blah abc foo 12345", c, 5, 8) is None
    assert ae.find_nearby_postal_code("12345 blah abc foo", c, 11, 14) is None
    # Search substring matching with postal code start
    assert ae.find_nearby_postal_code("foo 12345fr abc", c, 12, 15) == ("12345", 4, 9)

    # Invalid postal code (not 5 digits)
    m_get_logger = mocker.patch(f"{module}.get_logger")
    c2 = City("abc", "12A42", None)
    assert ae.find_nearby_postal_code("foo 12A42 abc", c2, 12, 15) is None
    m_get_logger.assert_called_once_with(f"{module}.AddressExtractor")
    m_get_logger.return_value.error.assert_called_once_with(
        "postal code contains non-digit characters: %s", c2
    )


def test_address_extractor_extract_addresses(mocker, cities):
    ae = AddressExtractor(
        cities, postal_code_search_distance=8, text_extract_distance=3
    )
    text = "blah paris 75000 poya foo"
    insights = ae.extract_addresses(text)
    assert len(insights) == 1
    assert insights[0].data == {
        "country_code": "fr",
        "city_name": "paris",
        "postal_code": "75000",
        "text_extract": "ah paris 75000 po",
    }

    text = "paris 75000 bar 98827fr poya foo"
    insights = ae.extract_addresses(text)
    assert len(insights) == 2
    assert insights[0].data == {
        "country_code": "fr",
        "city_name": "paris",
        "postal_code": "75000",
        "text_extract": "paris 75000 ba",
    }
    assert insights[1].data == {
        "country_code": "fr",
        "city_name": "poya",
        "postal_code": "98827",
        "text_extract": "ar 98827fr poya fo",
    }

    text = "blah paris foo 75000 bar"
    assert ae.extract_addresses(text) == []

    text = "blah paris 75000 paris foo"
    insights = ae.extract_addresses(text)
    assert insights[0].data == {
        "country_code": "fr",
        "city_name": "paris",
        "postal_code": "75000",
        "text_extract": "ah paris 75000 pa",
    }
    assert insights[1].data == {
        "country_code": "fr",
        "city_name": "paris",
        "postal_code": "75000",
        "text_extract": "is 75000 paris fo",
    }


def test_find_locations(mocker):
    m_extract_addresses = mocker.patch.object(AddressExtractor, "extract_addresses")

    assert find_locations(mocker.sentinel.content) == m_extract_addresses.return_value
    m_extract_addresses.assert_called_once_with(mocker.sentinel.content)
