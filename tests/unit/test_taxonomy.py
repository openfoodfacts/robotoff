import pytest

from robotoff.taxonomy import TaxonomyType, match_taxonomized_value


@pytest.mark.parametrize(
    "taxonomy_type,value,expected",
    [
        (TaxonomyType.brand.name, "carrefour-bio", "Carrefour BIO"),
        (TaxonomyType.brand.name, "turini", "Turini"),
        (TaxonomyType.brand.name, "unknown-brand", None),
        (TaxonomyType.label.name, "fr:bio-europeen", "en:eu-organic"),
        (
            TaxonomyType.label.name,
            "ab-agriculture-biologique",
            None,
        ),
        (
            TaxonomyType.label.name,
            "fr:ab-agriculture-biologique",
            "fr:ab-agriculture-biologique",
        ),
        (TaxonomyType.label.name, "unknown-label", None),
        (TaxonomyType.label.name, "fr:viande-bovine-francaise", "en:french-beef"),
        (TaxonomyType.ingredient.name, "text", None),  # unsupported taxonomy
        # en:shelled-almonds is the canonical ID, we check here that synonyms are
        # matched
        (TaxonomyType.category.name, "en:shelled-almonds", "en:shelled-almonds"),
    ],
)
def test_match_taxonomized_value(taxonomy_type, value, expected):
    assert match_taxonomized_value(value, taxonomy_type) == expected
