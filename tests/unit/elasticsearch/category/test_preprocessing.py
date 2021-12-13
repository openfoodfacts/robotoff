import pytest

from robotoff.elasticsearch.category.preprocessing import preprocess_name


@pytest.mark.parametrize(
    "name,lang,expected",
    [
        ("", "fr", ""),
        ("word  word", "en", "word word"),
        ("baguette 250g", "fr", "baguette"),
        ("BEURRE IGP", "fr", "beurre"),
        ("poulet fermier label ROUGE", "fr", "poulet fermier"),
        ("Parmigiano Reggiano ", "it", "parmigiano reggiano"),
    ],
)
def test_preprocess_name(name: str, lang: str, expected: str):
    assert preprocess_name(name, lang) == expected
