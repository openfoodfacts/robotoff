from typing import List
from robotoff.spellcheck.v2.base_spellchecker import BaseSpellchecker
from robotoff.spellcheck.v2.pipeline_spellchecker import PipelineSpellchecker
from robotoff.spellcheck.v2.items import (
    Offset,
    AtomicCorrection,
    SpellcheckIteration,
    SpellcheckItem,
    Ingredients,
)


class SpellcheckerV2(PipelineSpellchecker):
    def __init__(self, client, **es_kwargs):
        super(SpellcheckerV2, self).__init__()
        self.add_spellchecker("patterns")
        self.add_spellchecker("percentages")
        self.add_spellchecker("elasticsearch", client=client, **es_kwargs)
        self.add_spellchecker("vocabulary")
