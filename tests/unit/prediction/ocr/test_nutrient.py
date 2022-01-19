from typing import Dict, List

import pytest

from robotoff.prediction.ocr.nutrient import find_nutrient_mentions
from robotoff.utils.types import JSONType


@pytest.mark.parametrize(
    "text,nutrients",
    [
        ("valeurs nutritionnelles", {"nutrition_values": [{"languages": ["fr"]}]}),
        ("fibers", {"fiber": [{"languages": ["en"]}]}),
        ("fibres: 0.5g", {"fiber": [{"languages": ["en", "fr", "it"]}]}),
        ("ballaststoffe 5g", {"fiber": [{"languages": ["de"]}]}),
        (
            " gemiddelde waarden per 100 g",
            {"nutrition_values": [{"languages": ["nl"]}]},
        ),
        ("calories: 252kJ", {"energy": [{"languages": ["fr", "en"]}]}),
        ("waarvan verzadigde", {"saturated_fat": [{"languages": ["nl"]}]}),
        (
            "Sale - Salt 0,210 g",
            {"salt": [{"languages": ["it"]}, {"languages": ["en"]}]},
        ),
        ("acides gras saturés", {"saturated_fat": [{"languages": ["fr"]}]}),
        (
            "acides gras saturés 3.8g waarvan verzadigde",
            {"saturated_fat": [{"languages": ["fr"]}, {"languages": ["nl"]}]},
        ),
    ],
)
def test_find_nutrient_mentions(text: str, nutrients: Dict[str, List[JSONType]]):
    results = find_nutrient_mentions(text)
    assert len(results) == 1
    insight = results[0]
    assert "mentions" in insight.data
    mentions = insight.data["mentions"]

    for nutrient in nutrients:
        assert nutrient in mentions
        for ref, current in zip(nutrients[nutrient], mentions[nutrient]):
            for k, v in ref.items():
                assert k in current
                assert current[k] == v
