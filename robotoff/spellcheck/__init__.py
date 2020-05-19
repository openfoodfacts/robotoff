from typing import Optional, Iterable

from robotoff import settings
from robotoff.utils.types import JSONType
from robotoff.products import ProductDataset
from robotoff.spellcheck.pipeline_spellchecker import PipelineSpellchecker


class Spellchecker(PipelineSpellchecker):
    def __init__(self, client, **es_kwargs):
        super(Spellchecker, self).__init__()
        self.es_kwargs = es_kwargs
        self.add_spellchecker("patterns")
        self.add_spellchecker("percentages")
        self.add_spellchecker("elasticsearch", client=client, **es_kwargs)
        self.add_spellchecker("vocabulary")

    def generate_insights(
        self,
        detailed: bool = False,
        max_errors: Optional[int] = None,
        lang: str = "fr",
        limit: Optional[int] = None,
    ) -> Iterable[JSONType]:

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
                insight = self.predict_insight(
                    product["ingredients_text_fr"], detailed=detailed,
                )
                if insight is not None:
                    insight["lang"] = lang
                    insight["barcode"] = product["code"]
                    yield insight

                    insights_count += 1
                    if limit is not None and insights_count >= limit:
                        break

    def predict_insight(self, text: str, detailed: bool) -> Optional[JSONType]:
        corrected_text = self.correct(text)
        if corrected_text != text:
            insight = {
                "text": text,
                "corrected": corrected_text,
                "index_name": self.es_kwargs.get(
                    "index_name", settings.ELASTICSEARCH_PRODUCT_INDEX
                ),
            }
            if detailed:
                insight["corrections"] = self.get_corrections()
            return insight
        return None

    @staticmethod
    def is_product_valid(product: JSONType, max_errors: Optional[int] = None) -> bool:
        if max_errors is None:
            return True
        else:
            return int(product.get("unknown_ingredients_n", 0)) <= max_errors
