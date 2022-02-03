import abc
from typing import Optional

from robotoff.insights._enum import InsightType
from robotoff.models import ProductInsight
from robotoff.products import ProductStore
from robotoff.taxonomy import TAXONOMY_STORES, Taxonomy
from robotoff.utils.types import JSONType


class InsightValidator(metaclass=abc.ABCMeta):
    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    @staticmethod
    @abc.abstractmethod
    def get_type() -> str:
        pass

    @abc.abstractmethod
    def is_valid(self, insight: ProductInsight) -> bool:
        pass


class LabelValidator(InsightValidator):
    @staticmethod
    def get_type() -> str:
        return InsightType.label.name

    def is_valid(self, insight: ProductInsight) -> bool:
        product = self.product_store[insight.barcode]
        product_labels_tags = getattr(product, "labels_tags", [])
        label_tag = insight.value_tag

        if label_tag in product_labels_tags:
            return False

        # Check that the predicted label is not a parent of a
        # current/already predicted label
        label_taxonomy: Taxonomy = TAXONOMY_STORES[InsightType.label.name].get()

        if label_tag in label_taxonomy and label_taxonomy.is_parent_of_any(
            label_tag, product_labels_tags
        ):
            return False

        return True


class CategoryValidator(InsightValidator):
    @staticmethod
    def get_type() -> str:
        return InsightType.category.name

    def is_valid(self, insight: ProductInsight) -> bool:
        product = self.product_store[insight.barcode]
        product_categories_tags = getattr(product, "categories_tags", [])
        category_tag = insight.value_tag

        if category_tag in product_categories_tags:
            return False

        # Check that the predicted category is not a parent of a
        # current/already predicted category
        category_taxonomy: Taxonomy = TAXONOMY_STORES[InsightType.category.name].get()

        if category_tag in category_taxonomy and category_taxonomy.is_parent_of_any(
            category_tag, product_categories_tags
        ):
            return False

        return True


class InsightValidatorFactory:
    validators: JSONType = {
        InsightType.label.name: LabelValidator,
        InsightType.category.name: CategoryValidator,
    }

    @classmethod
    def create(
        cls, insight_type: str, product_store: Optional[ProductStore]
    ) -> Optional[InsightValidator]:
        if insight_type in cls.validators:
            return cls.validators[insight_type](product_store)
        else:
            return None
