import abc
import enum
from typing import Optional

from robotoff.brands import BRAND_BLACKLIST_STORE, BRAND_PREFIX_STORE, in_barcode_range
from robotoff.insights.dataclass import InsightType
from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import ProductInsight
from robotoff.products import Product, ProductStore, is_valid_image
from robotoff.taxonomy import Taxonomy, get_taxonomy
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


class InsightValidator(metaclass=abc.ABCMeta):
    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    def has_invalid_image(
        self, insight: ProductInsight, product: Optional[Product] = None
    ) -> bool:
        if (
            product
            and insight.source_image
            and not is_valid_image(product.images, insight.source_image)
        ):
            return True

        return False

    def is_valid(
        self, insight: ProductInsight, product: Optional[Product] = None
    ) -> Optional[bool]:
        if product is None:
            product = self.product_store[insight.barcode]

        return not self.has_invalid_image(insight, product)


class BrandValidator(InsightValidator):
    def is_valid(self, insight: ProductInsight, product: Optional[Product] = None):
        if product is None:
            product = self.product_store[insight.barcode]

        if self.has_invalid_image(insight, product):
            return False

        brand_prefix = BRAND_PREFIX_STORE.get()
        brand_tag = insight.value_tag
        barcode = insight.barcode

        if not in_barcode_range(brand_prefix, brand_tag, barcode):
            logger.info(
                "Barcode {} of brand {} not in barcode "
                "range".format(barcode, brand_tag)
            )
            return False

        if brand_tag in BRAND_BLACKLIST_STORE.get():
            return False

        brand_tag = insight.value_tag

        if product is None:
            return True

        if brand_tag in product.brands_tags:
            return False

        return True


class LabelValidator(InsightValidator):
    def is_valid(
        self, insight: ProductInsight, product: Optional[Product] = None
    ) -> bool:
        if product is None:
            product = self.product_store[insight.barcode]

        product_labels_tags = getattr(product, "labels_tags", [])
        label_tag = insight.value_tag

        if label_tag in product_labels_tags:
            return False

        # Check that the predicted label is not a parent of a
        # current/already predicted label
        label_taxonomy: Taxonomy = get_taxonomy(InsightType.label.name)

        if label_tag in label_taxonomy and label_taxonomy.is_parent_of_any(
            label_tag, product_labels_tags
        ):
            return False

        return True


class CategoryValidator(InsightValidator):
    def is_valid(
        self, insight: ProductInsight, product: Optional[Product] = None
    ) -> bool:
        if product is None:
            product = self.product_store[insight.barcode]

        product_categories_tags = getattr(product, "categories_tags", [])
        category_tag = insight.value_tag

        if category_tag in product_categories_tags:
            return False

        # Check that the predicted category is not a parent of a
        # current/already predicted category
        category_taxonomy: Taxonomy = get_taxonomy(InsightType.category.name)

        if category_tag in category_taxonomy and category_taxonomy.is_parent_of_any(
            category_tag, product_categories_tags
        ):
            return False

        return True


class ProductWeightValidator(InsightValidator):
    def is_valid(
        self, insight: ProductInsight, product: Optional[Product] = None
    ) -> bool:
        if product is None:
            product = self.product_store[insight.barcode]

        if product is None:
            return True

        if product.quantity is not None:
            return False

        return True


class ExpirationDateValidator(InsightValidator):
    def is_valid(
        self, insight: ProductInsight, product: Optional[Product] = None
    ) -> bool:
        if product is None:
            product = self.product_store[insight.barcode]

        if not product:
            return True

        if product.expiration_date:
            return False

        return True


class PackagerCodeValidator(InsightValidator):
    def is_valid(
        self, insight: ProductInsight, product: Optional[Product] = None
    ) -> bool:
        if product is None:
            product = self.product_store[insight.barcode]

        product_emb_codes_tags = getattr(product, "emb_codes_tags", [])

        normalized_emb_code = normalize_emb_code(insight.value)
        normalized_emb_codes = [normalize_emb_code(c) for c in product_emb_codes_tags]

        if normalized_emb_code in normalized_emb_codes:
            return False

        return True


class InsightValidatorFactory:
    validators: JSONType = {
        InsightType.label.name: LabelValidator,
        InsightType.category.name: CategoryValidator,
        InsightType.product_weight.name: ProductWeightValidator,
        InsightType.brand.name: BrandValidator,
        InsightType.expiration_date.name: ExpirationDateValidator,
        InsightType.packager_code.name: PackagerCodeValidator,
    }

    @classmethod
    def create(
        cls, insight_type: str, product_store: Optional[ProductStore]
    ) -> Optional[InsightValidator]:
        if insight_type in cls.validators:
            return cls.validators[insight_type](product_store)
        else:
            return None


@enum.unique
class InsightValidationResult(enum.IntEnum):
    unchanged = 0
    deleted = 1


def validate_insight(
    insight: ProductInsight,
    validator: Optional[InsightValidator],
    product: Optional[Product] = None,
) -> InsightValidationResult:
    if validator is None:
        return InsightValidationResult.unchanged

    if not validator.is_valid(insight, product=product):
        insight.delete_instance()
        return InsightValidationResult.deleted

    return InsightValidationResult.unchanged
