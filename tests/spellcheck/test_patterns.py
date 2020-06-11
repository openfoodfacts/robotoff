import pytest

from robotoff.spellcheck.patterns import PatternsSpellchecker


spellchecker = PatternsSpellchecker()


@pytest.mark.parametrize(
    "text,correction",
    [
        ("ﬁlet de poulet", "filet de poulet"),
        ("filet de poulet", "filet de poulet"),
        ("2 FILETS DE POULET", "2 FILETS DE POULET"),
        ("correcteur dacidité", "correcteur d'acidité"),
        ("baton decanelle", "baton decannelle"),
        ("Viande de bceuf", "Viande de bœuf"),
        ("Viande de Bceuf", "Viande de Bœuf"),
        ("oeuf de poule", "œuf de poule"),
        ("Oeuf de poule", "Œuf de poule"),
        ("OEUF de poule", "ŒUF de poule"),
    ],
)
def test_patterns(text: str, correction: str):
    assert spellchecker.correct(text) == correction
