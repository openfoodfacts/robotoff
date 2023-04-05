from typing import Iterable, Optional, Union

from robotoff import settings
from robotoff.products import ProductDataset
from robotoff.spellcheck.base_spellchecker import BaseSpellchecker
from robotoff.spellcheck.elasticsearch import ElasticSearchSpellchecker
from robotoff.spellcheck.items import SpellcheckItem
from robotoff.spellcheck.patterns import PatternsSpellchecker
from robotoff.spellcheck.percentages import PercentagesSpellchecker
from robotoff.spellcheck.vocabulary import VocabularySpellchecker
from robotoff.types import JSONType, Prediction, PredictionType

SPELLCHECKERS = {
    "elasticsearch": ElasticSearchSpellchecker,
    "patterns": PatternsSpellchecker,
    "percentages": PercentagesSpellchecker,
    "vocabulary": VocabularySpellchecker,
}


class Spellchecker:
    def __init__(self, pipeline: list[BaseSpellchecker]):
        self.spellcheckers: list[BaseSpellchecker] = pipeline

    @classmethod
    def load(
        cls,
        client,
        pipeline: Optional[list[Union[str, BaseSpellchecker]]] = None,
        **es_kwargs,
    ):
        pipeline_: list[BaseSpellchecker] = []

        if pipeline is None:
            pipeline = ["patterns", "elasticsearch", "vocabulary"]

        for item in pipeline:
            if isinstance(item, str):
                if item not in SPELLCHECKERS:
                    raise ValueError(
                        f"Spellchecker {item} not found. Available : {list(SPELLCHECKERS.keys())}"
                    )

                if item == "elasticsearch":
                    base_spellchecker = ElasticSearchSpellchecker(client, **es_kwargs)
                else:
                    base_spellchecker = SPELLCHECKERS[item]()

                pipeline_.append(base_spellchecker)

            elif not isinstance(item, BaseSpellchecker):
                raise TypeError(
                    f"invalid item in pipeline: {item}, expected str or BaseSpellchecker"
                )
                pipeline_.append(item)

        return cls(pipeline_)

    def generate_insights(
        self,
        max_errors: Optional[int] = None,
        lang: str = "fr",
        limit: Optional[int] = None,
    ) -> Iterable[Prediction]:
        dataset = ProductDataset(settings.JSONL_DATASET_PATH)
        product_iter = (
            dataset.stream()
            .filter_by_country_tag("en:france")
            .filter_text_field("lang", lang)
            .filter_nonempty_text_field("ingredients_text_fr")
            .iter()
        )

        insights_count = 0
        for product in product_iter:
            if self.is_product_valid(product, max_errors=max_errors):
                insight = self.predict_insight(product["ingredients_text_fr"])
                if insight is not None:
                    insight["lang"] = lang
                    yield Prediction(
                        type=PredictionType.ingredient_spellcheck,
                        data=insight,
                        barcode=product["code"],
                    )

                    insights_count += 1
                    if limit is not None and insights_count >= limit:
                        break

    def predict_insight(self, text: str) -> Optional[JSONType]:
        correction_item = self.correct(text)
        corrected_text = correction_item.latest_correction
        if corrected_text != text:
            insight: JSONType = {
                "text": text,
                "corrected": corrected_text,
            }
            insight["corrections"] = correction_item.corrections
            insight["config"] = [s.get_config() for s in self.spellcheckers]
            return insight

        return None

    @staticmethod
    def is_product_valid(product: JSONType, max_errors: Optional[int] = None) -> bool:
        if max_errors is None:
            return True
        else:
            return int(product.get("unknown_ingredients_n", 0)) <= max_errors

    def correct(self, text: str) -> SpellcheckItem:
        item = SpellcheckItem(text)
        if item.is_lang_allowed:
            for spellcheck in self.spellcheckers:
                spellcheck.predict([item])
        return item
