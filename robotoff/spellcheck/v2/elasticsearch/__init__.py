from typing import Dict, List

from robotoff.spellcheck.v2.base_spellchecker import BaseSpellchecker
from robotoff.spellcheck.v2.exceptions import TokenLengthMismatchException
from robotoff.spellcheck.v2.items import (
    Ingredients,
    AtomicCorrection,
    SpellcheckIteration,
    SpellcheckItem,
)

from robotoff.spellcheck.v2.elasticsearch.ingredients_splitter import (
    IngredientsSplitter,
)
from robotoff.spellcheck.v2.elasticsearch.correction_formatter import (
    CorrectionFormatter,
)
from robotoff.spellcheck.v2.elasticsearch.es_handler import ElasticsearchHandler


class ElasticSearchSpellchecker(BaseSpellchecker):

    SPLITTER = IngredientsSplitter()

    def __init__(self, client, **kwargs):
        self.client = client
        self.kwargs = kwargs

    @property
    def name(self) -> str:
        return super(ElasticSearchSpellchecker, self).name + "".join(
            [f"__{kw}_{value}" for kw, value in self.kwargs]
        )

    def predict_one(self, item: SpellcheckItem) -> SpellcheckItem:
        original = item.latest_correction
        atomic_corrections = self._process(original)
        item.iterations.append(
            SpellcheckIteration(
                model=self.name,
                original=original,
                atomic_corrections=atomic_corrections,
            )
        )
        return item

    def correct(self, text: str) -> str:
        return SpellcheckIteration(
            original=text, atomic_corrections=self._process(text)
        ).corrected_text

    def _process(self, text: str) -> List[AtomicCorrection]:
        es_handler = ElasticsearchHandler(self.client, **self.kwargs)
        correction_formatter = CorrectionFormatter()

        ingredients: Ingredients = self.SPLITTER.split(text)
        suggestions = es_handler.suggest_batch(iter(ingredients))

        corrections = []
        for idx, suggestion in enumerate(suggestions):
            if not suggestion.get("options"):
                continue
            main_option = suggestion["options"][0]

            try:
                corrections.extend(
                    correction_formatter.format(
                        original_tokens=es_handler.analyze(
                            ingredients.get_normalized_ingredient_text(idx)
                        ),
                        suggestion_tokens=es_handler.analyze(main_option["text"]),
                        offset=ingredients.offsets[idx],
                        score=main_option["score"],
                    )
                )
            except TokenLengthMismatchException:
                continue

        for correction in corrections:
            correction.model = self.name

        return corrections
