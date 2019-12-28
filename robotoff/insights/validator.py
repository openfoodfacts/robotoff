import abc
from typing import Optional

from robotoff.brands import BRAND_PREFIX_STORE, in_barcode_range
from robotoff.insights._enum import InsightType
from robotoff.models import ProductInsight
from robotoff.products import ProductStore, Product
from robotoff.taxonomy import Taxonomy, get_taxonomy
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType


logger = get_logger(__name__)


class InsightValidator(metaclass=abc.ABCMeta):
    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    @staticmethod
    @abc.abstractmethod
    def get_type() -> str:
        pass

    @abc.abstractmethod
    def is_valid(self, insight: ProductInsight,
                 product: Optional[Product] = None) -> bool:
        pass


class BrandValidator(InsightValidator):
    @staticmethod
    def get_type() -> str:
        return InsightType.brand.name

    def is_valid(self, insight: ProductInsight,
                 product: Optional[Product] = None):
        brand_prefix = BRAND_PREFIX_STORE.get()
        brand_tag = insight.value_tag
        barcode = insight.barcode

        if not in_barcode_range(brand_prefix, brand_tag, barcode):
            logger.info("Barcode {} of brand {} not in barcode "
                        "range".format(barcode, brand_tag))
            return False

        if product is None:
            product = self.product_store[insight.barcode]

            if product is None:
                return True

        if brand_tag in product.brands_tags:
            return False

        return True


class LabelValidator(InsightValidator):
    @staticmethod
    def get_type() -> str:
        return InsightType.label.name

    def is_valid(self, insight: ProductInsight,
                 product: Optional[Product] = None) -> bool:
        if product is None:
            product = self.product_store[insight.barcode]

        product_labels_tags = getattr(product, 'labels_tags', [])
        label_tag = insight.value_tag

        if label_tag in product_labels_tags:
            return False

        # Check that the predicted label is not a parent of a
        # current/already predicted label
        label_taxonomy: Taxonomy = get_taxonomy(InsightType.label.name)

        if (label_tag in label_taxonomy and
            label_taxonomy.is_parent_of_any(label_tag,
                                            product_labels_tags)):
            return False

        return True


class CategoryValidator(InsightValidator):
    @staticmethod
    def get_type() -> str:
        return InsightType.category.name

    def is_valid(self, insight: ProductInsight,
                 product: Optional[Product] = None) -> bool:
        if product is None:
            product = self.product_store[insight.barcode]

        product_categories_tags = getattr(product, 'categories_tags', [])
        category_tag = insight.value_tag

        if category_tag in product_categories_tags:
            return False

        # Check that the predicted category is not a parent of a
        # current/already predicted category
        category_taxonomy: Taxonomy = get_taxonomy(InsightType.category.name)

        if (category_tag in category_taxonomy and
            category_taxonomy.is_parent_of_any(category_tag,
                                               product_categories_tags)):
            return False

        return True


class ProductWeightValidator(InsightValidator):
    @staticmethod
    def get_type() -> str:
        return InsightType.product_weight.name

    def is_valid(self, insight: ProductInsight,
                 product: Optional[Product] = None) -> bool:
        if product is None:
            product = self.product_store[insight.barcode]

            if product is None:
                # Product is not in product store yet, keep the insight
                return True

        if product.quantity is not None:
            return False

        return True


class InsightValidatorFactory:
    validators: JSONType = {
        InsightType.label.name: LabelValidator,
        InsightType.category.name: CategoryValidator,
        InsightType.product_weight.name: ProductWeightValidator,
        InsightType.brand.name: BrandValidator,
    }

    @classmethod
    def create(cls, insight_type: str,
               product_store: Optional[ProductStore]) -> \
            Optional[InsightValidator]:
        if insight_type in cls.validators:
            return cls.validators[insight_type](product_store)
        else:
            return None


def delete_invalid_insight(insight: ProductInsight,
                           validator: Optional[InsightValidator],
                           product: Optional[Product] = None) -> bool:
    if validator is None:
        return False

    if not validator.is_valid(insight, product=product):
        insight.delete_instance()
        return True

    return False
