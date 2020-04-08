from pathlib import Path

from robotoff.insights.ocr.location import (
    City,
    AddressExtractor,
    load_cities_fr,
    remove_accents,
    CITIES_FR_RESOURCE,
)


module = "robotoff.insights.ocr.location"


def test_load_cities_fr(mocker):
    m_open_binary = mocker.patch(f"{module}.open_binary")
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

    m_open_binary.assert_called_once_with(*CITIES_FR_RESOURCE)
    m_gzip_open.assert_called_once_with(
        m_open_binary.return_value.__enter__.return_value, "rb"
    )
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


def test_remove_accents():
    assert remove_accents("àéèïçč") == "aeeicc"
    assert remove_accents("aeeicc") == "aeeicc"
    assert remove_accents("ÀÉÈÏÇČ'_$^") == "AEEICC'_$^"
    assert remove_accents("AEEICC'_$^") == "AEEICC'_$^"


def test_city_extractor():
    c1 = City("abc", "12345", None)
    c2 = City("def g", "12345", None)
    ce = AddressExtractor([c1, c2])

    assert ce.find_city_names("without city") == []
    assert ce.find_city_names("with def and g") == []
    assert ce.find_city_names("with the abc city") == [(c1, 9, 12)]
    assert ce.find_city_names("with the def g city") == [(c2, 9, 14)]
    assert ce.find_city_names("with def g and abc cities") == [
        (c2, 5, 10), (c1, 15, 18)]
    # To fix
    assert ce.find_city_names("with àbç and déf g with accents") == [
        (c1, 5, 8), (c2, 13, 18)]
    assert ce.find_city_names("with def'g and l'abc and def-g") == [
        (c2, 5, 10), (c1, 17, 20), (c2, 25, 30)]
