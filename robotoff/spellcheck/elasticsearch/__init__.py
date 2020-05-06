from typing import Dict, List

from robotoff.spellcheck import BaseSpellchecker
from robotoff.spellcheck.data_utils import Ingredients, Correction
from robotoff.spellcheck.elasticsearch.ingredients_splitter import IngredientsSplitter
from robotoff.spellcheck.elasticsearch.correction_formatter import CorrectionFormatter
from robotoff.spellcheck.elasticsearch.es_handler import ElasticsearchHandler


class ElasticSearchSpellchecker(BaseSpellchecker):

    SPLITTER = IngredientsSplitter()

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @property
    def name(self):
        return super(ElasticSearchSpellchecker, self).name + "".join(
            [f"__{kw}_{value}" for kw, value in self.kwargs]
        )

    def correct(self, text: str) -> str:
        raise NotImplementedError

    def process(self, client, text: str) -> List[Correction]:
        es_handler = ElasticsearchHandler(client, **self.kwargs)
        correction_formatter = CorrectionFormatter()

        ingredients: Ingredients = self.SPLITTER.split(text)
        suggestions = es_handler.suggest_batch(iter(ingredients))

        corrections = []
        for idx, suggestion in enumerate(suggestions):
            if not suggestion.options:
                continue
            main_option = suggestion.options[0]

            try:
                corrections.append(
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

        return corrections

    def test(self, text):
        ingredients = self.SPLITTER.split(text)
        print(ingredients)
        import code

        code.interact(local=dict(locals(), **globals()))
