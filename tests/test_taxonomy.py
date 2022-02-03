from typing import List

import pytest

from robotoff import settings
from robotoff.taxonomy import Taxonomy

label_taxonomy = Taxonomy.from_json(settings.TAXONOMY_LABEL_PATH)


class TestTaxonomy:
    @pytest.mark.parametrize(
        "taxonomy,item,candidates,output",
        [
            (label_taxonomy, "en:organic", {"en:fr-bio-01"}, True),
            (label_taxonomy, "en:fr-bio-01", {"en:organic"}, False),
            (label_taxonomy, "en:fr-bio-01", [], False),
            (label_taxonomy, "en:organic", {"en:gluten-free"}, False),
            (
                label_taxonomy,
                "en:organic",
                {"en:gluten-free", "en:no-additives", "en:vegan"},
                False,
            ),
            (
                label_taxonomy,
                "en:organic",
                {"en:gluten-free", "en:no-additives", "en:fr-bio-16"},
                True,
            ),
        ],
    )
    def test_is_child_of_any(
        self, taxonomy: Taxonomy, item: str, candidates: List, output: bool
    ):
        assert taxonomy.is_parent_of_any(item, candidates) is output

    def test_is_child_of_any_unknwon_item(self):
        with pytest.raises(ValueError):
            label_taxonomy.is_parent_of_any("unknown-id", set())
