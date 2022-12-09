from robotoff.spellcheck.base_spellchecker import BaseSpellchecker
from robotoff.spellcheck.elasticsearch.correction_formatter import CorrectionFormatter
from robotoff.spellcheck.elasticsearch.es_handler import ElasticsearchHandler
from robotoff.spellcheck.exceptions import TokenLengthMismatchException
from robotoff.spellcheck.items import (
    AtomicCorrection,
    Ingredients,
    SpellcheckItem,
    SpellcheckIteration,
)

VERSION = "1"


class ElasticSearchSpellchecker(BaseSpellchecker):
    def __init__(self, client, **kwargs):
        self.client = client
        self.kwargs = kwargs

    @property
    def name(self) -> str:
        return super(ElasticSearchSpellchecker, self).name + "".join(
            [f"__{kw}_{value}" for kw, value in self.kwargs.items()]
        )

    def predict_one(self, item: SpellcheckItem) -> SpellcheckItem:
        if item.is_lang_allowed:
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

    def _process(self, text: str) -> list[AtomicCorrection]:
        es_handler = ElasticsearchHandler(self.client, **self.kwargs)
        correction_formatter = CorrectionFormatter()

        ingredients: Ingredients = Ingredients.from_text(text)
        suggestions = es_handler.suggest_batch(ingredients.get_iter())

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

    def get_config(self):
        return {
            "version": VERSION,
            "name": self.__class__.__name__,
            **self.kwargs,
        }
