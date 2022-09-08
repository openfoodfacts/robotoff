from typing import Dict, List, Union

import pytest

from robotoff.prediction.ocr.origin import LARGE_ORIGIN, find_origin
from robotoff.utils.types import JSONType


@pytest.mark.parametrize(
    "text,origins",
    [
        #French ----------
        ("quinoa fait en France", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("quinoa français", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("quinoa de France", [{"origin": "France", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("Notre quinoa est produit en France", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("Quinoa 100% français", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("quinoa cultivée en dehors de l' Union Européenne", [{"origin": LARGE_ORIGIN, "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("produit en France", [{"origin": "en:france", "same_for_all_ingredients": True, "concerned_ingredients": None}]),
        ("Tout les ingrédients sont fabriqués en France", [{"origin": "en:france", "same_for_all_ingredients": True, "concerned_ingredients": None}]),
        ("Le quinoa a diverse origines", [{"origin": LARGE_ORIGIN, "same_for_all_ingredients": True, "concerned_ingredients": None}]),
        ("Quinoa et riz français", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa", "en:rice"]}]),
        ("Quinoa et riz français, et blé allemand", 
        [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa", "en:rice"]},
         {"origin": "en:germany", "same_for_all_ingredients": False, "concerned_ingredients": ["en:wheat"]}]),
        ("""Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent in tincidunt est. Praesent et eros felis.
        Pellentesque tempus, quam et vestibulum condimentum, risus elit varius erat, eget auctor nibh quam at lorem.
        Donec enim quam, egestas sed tincidunt id, consequat et lorem. Donec eget tincidunt ipsum, 
        vel efficitur nibh. Aliquam leo nulla, cursus vel risus eu, fringilla finibus orci. Mauris in pulvinar ante.
        Curabitur luctus velit quam, vel placerat orci faucibus suscipit. In pretium molestie nisl, at lacinia nisl ullamcorper eget.
        Curabitur euismod nulla id mauris vehicula lacinia. Suspendisse ullamcorper tristique vestibulum.
        Aliquam pretium in lectus at pellentesque. Etiam non consequat ipsum. Nunc condimentum ipsum orci,
        at lobortis lorem vestibulum vitae. Maecenas a facilisis ipsum. Sed maximus lobortis lectus sed auctor.

        Sed vel ipsum quis est scelerisque consectetur.
        Aenean et neque quis felis consequat viverra in at lacus.
        Nunc condimentum massa sit amet risus elementum scelerisque. 
        Donec mollis non orci sit amet tempus. Sed vel velit vehicula, finibus urna a, feugiat velit. In vitae lobortis justo. 
        Morbi vitae metus vehicula velit cursus vulputate blandit ac mauris. Quinoa et riz français, et blé allemand 
        Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. 
        Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Duis condimentum ante in rhoncus pharetra. 
        Vivamus in eros in nisi rutrum tristique. Sed posuere, leo et maximus faucibus, nisi metus tempus justo, 
        eget mollis nisi felis id ipsum. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae""", 
        [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa", "en:rice"]},
         {"origin": "en:germany", "same_for_all_ingredients": False, "concerned_ingredients": ["en:wheat"]}]),
        # English -----------------
        ("quinoa made in France", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("french quinoa", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("quinoa from France", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("Our quinoa is produced in France", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("100% french Quinoa", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("quinoa farmed outside the European Union", [{"origin": LARGE_ORIGIN, "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa"]}]),
        ("produced in France", [{"origin": "en:france", "same_for_all_ingredients": True, "concerned_ingredients": None}]),
        ("Every ingredients are made in France", [{"origin": "en:france", "same_for_all_ingredients": True, "concerned_ingredients": None}]),
        ("The quinoa has several origins", [{"origin": LARGE_ORIGIN, "same_for_all_ingredients": True, "concerned_ingredients": None}]),
        ("French quinoa and rice", [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa", "en:rice"]}]),
        ("French quinoa and rice, and german wheat", 
        [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa", "en:rice"]},
         {"origin": "en:germany", "same_for_all_ingredients": False, "concerned_ingredients": ["en:wheat"]}]),
        ("""Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent in tincidunt est. Praesent et eros felis.
        Pellentesque tempus, quam et vestibulum condimentum, risus elit varius erat, eget auctor nibh quam at lorem.
        Donec enim quam, egestas sed tincidunt id, consequat et lorem. Donec eget tincidunt ipsum, 
        vel efficitur nibh. Aliquam leo nulla, cursus vel risus eu, fringilla finibus orci. Mauris in pulvinar ante.
        Curabitur luctus velit quam, vel placerat orci faucibus suscipit. In pretium molestie nisl, at lacinia nisl ullamcorper eget.
        Curabitur euismod nulla id mauris vehicula lacinia. Suspendisse ullamcorper tristique vestibulum.
        Aliquam pretium in lectus at pellentesque. Etiam non consequat ipsum. Nunc condimentum ipsum orci,
        at lobortis lorem vestibulum vitae. Maecenas a facilisis ipsum. Sed maximus lobortis lectus sed auctor.

        Sed vel ipsum quis est scelerisque consectetur.
        Aenean et neque quis felis consequat viverra in at lacus.
        Nunc condimentum massa sit amet risus elementum scelerisque. 
        Donec mollis non orci sit amet tempus. Sed vel velit vehicula, finibus urna a, feugiat velit. In vitae lobortis justo. 
        Morbi vitae metus vehicula velit cursus vulputate blandit ac mauris. French quinoa and rice, and german wheat 
        Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. 
        Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Duis condimentum ante in rhoncus pharetra. 
        Vivamus in eros in nisi rutrum tristique. Sed posuere, leo et maximus faucibus, nisi metus tempus justo, 
        eget mollis nisi felis id ipsum. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae""", 
        [{"origin": "en:france", "same_for_all_ingredients": False, "concerned_ingredients": ["en:quinoa", "en:rice"]},
         {"origin": "en:germany", "same_for_all_ingredients": False, "concerned_ingredients": ["en:wheat"]}])
    ],
)
def test_find_origin(text: str, origins: List[Dict[str, Union[str, List[str], bool]]]):
    results = find_origin(text)
    for index, insight in enumerate(results):
        assert "ingredients_origins" in insight.data
        assert insight.data["ingredients_origins"] == origins[index]
