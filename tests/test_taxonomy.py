from typing import List, Set

import pytest

from robotoff import settings
from robotoff.taxonomy import Taxonomy


label_taxonomy = Taxonomy.from_json(settings.TAXONOMY_LABEL_PATH)
category_taxonomy = Taxonomy.from_json(settings.TAXONOMY_CATEGORY_PATH)


class TestTaxonomy:
    @pytest.mark.parametrize('taxonomy,item,candidates,output', [
        (label_taxonomy, 'en:organic', {'en:fr-bio-01'}, True),
        (label_taxonomy, 'en:fr-bio-01', {'en:organic'}, False),
        (label_taxonomy, 'en:fr-bio-01', [], False),
        (label_taxonomy, 'en:organic', {'en:gluten-free'}, False),
        (label_taxonomy, 'en:organic',
         {'en:gluten-free', 'en:no-additives', 'en:vegan'}, False),
        (label_taxonomy, 'en:organic',
         {'en:gluten-free', 'en:no-additives', 'en:fr-bio-16'}, True),
    ])
    def test_is_child_of_any(self, taxonomy: Taxonomy, item: str,
                             candidates: List, output: bool):
        assert taxonomy.is_parent_of_any(item, candidates) is output

    def test_is_child_of_any_unknwon_item(self):
        with pytest.raises(ValueError):
            label_taxonomy.is_parent_of_any("unknown-id", set())

    @pytest.mark.parametrize('taxonomy,item,output', [
        (category_taxonomy, 'en:plant-based-foods-and-beverages', set()),
        (category_taxonomy, 'en:plant-based-foods', {'en:plant-based-foods-and-beverages'}),
        (category_taxonomy, 'en:brown-rices', {'en:rices', 'en:cereal-grains',
                                               'en:cereals-and-their-products',
                                               'en:cereals-and-potatoes', 'en:plant-based-foods',
                                               'en:plant-based-foods-and-beverages', 'en:seeds'}),
    ])
    def test_get_parents_hierarchy(self, taxonomy: Taxonomy,
                                   item: str,
                                   output: Set[str]):
        node = taxonomy[item]
        parents = node.get_parents_hierarchy()
        assert set((x.id for x in parents)) == output

    @pytest.mark.parametrize('taxonomy,items,output', [
        (category_taxonomy, [], []),
        (category_taxonomy, ['en:brown-rices'], ['en:brown-rices']),
        (category_taxonomy, ['en:brown-rices', 'en:rices'], ['en:brown-rices']),
        (category_taxonomy, ['en:brown-rices', 'en:rices', 'en:cereal-grains'],
         ['en:brown-rices']),
        (category_taxonomy, ['en:brown-rices', 'en:teas', 'en:cereal-grains'],
         ['en:brown-rices', 'en:teas']),
    ])
    def test_find_deepest_nodes(self, taxonomy: Taxonomy,
                                items: List[str],
                                output: List[str]):
        item_nodes = [taxonomy[item] for item in items]
        output_nodes = [taxonomy[o] for o in output]
        assert taxonomy.find_deepest_nodes(item_nodes) == output_nodes
