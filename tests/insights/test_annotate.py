
import pytest

from robotoff.insights.annotate import IngredientSpellcheckAnnotator


class TestIngredientSpellCheckAnnotator:
    @pytest.mark.parametrize('ingredient_str,start_offset,end_offset,correction,expected', [
        ("fqrine de blé complet", 0, 6, "farine", "farine de blé complet"),
        ("farine de blé complet, paudre à lever", 23, 29, "poudre", "farine de blé complet, poudre à lever"),
    ])
    def test_generate_full_correction(self, ingredient_str, start_offset, end_offset, correction, expected):
        assert IngredientSpellcheckAnnotator.generate_full_correction(ingredient_str,
                                                                      start_offset, end_offset, correction) == expected
