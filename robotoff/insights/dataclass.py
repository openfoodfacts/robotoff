import dataclasses
import datetime
from enum import Enum, unique
from typing import Any, Dict, List, Optional

from robotoff.prediction.types import Prediction, ProductPredictions


@unique
class InsightType(str, Enum):
    """InsightType defines the type of the insight."""

    # The 'ingredient spellcheck' insight corrects the spelling in the given ingredients list.
    # NOTE: this insight currently relies on manual imports - it's possible these insights have
    # not been generated recently.
    ingredient_spellcheck = "ingredient_spellcheck"

    # The 'packager code' insight extracts the packager code using regex from the image OCR.
    # This insight is always applied automatically.
    packager_code = "packager_code"

    # The 'label' insight predicts a label that appears on the product packaging photo.
    #  Several labels are possible:
    #   - Nutriscore label detection.
    #   - Logo detection using the universal logo detector.
    #   - OCR labeling based on text parsing.
    label = "label"

    # The 'category' insight predicts the category of a product.
    # This insight can be generated by 2 different predictors:
    #  1. The Keras ML category classifier.
    #  2. The Elasticsearch category predictor based on product name.
    #
    # NOTE: there also exists a hierachical category classifier, but it hasn't generated any
    # insights since 2019.
    category = "category"

    # The 'image_flag' insight flags inappropriate images based on OCR text.
    # This insight type is never persisted to the Postgres DB and is only used to pass insight information
    # in memory.
    #
    # Currently 3 possible sources of flagged images are possible:
    #  1) "safe_search_annotation" - Google's SafeSearch API detects explicit content on product images.
    #  2) "label_annotation" - a list of hard-coded labels that should be flagged that are found on the image's OCR.
    #  3) Flashtext matches on the image's OCR.
    image_flag = "image_flag"

    # The 'product_weight' insight extracts the product weight from the image OCR.
    # This insight is never applied automatically.
    product_weight = "product_weight"

    # The 'expiration_date' insight extracts the expiration date from the image OCR.
    expiration_date = "expiration_date"

    # The 'brand' insight extracts the product's brand from the image OCR.
    brand = "brand"

    # The 'image_orientation' insight predicts the image orientation of the given image.
    image_orientation = "image_orientation"

    # The 'store' insight detects the store where the given product is sold from the image OCR.
    store = "store"

    # The 'nutrient' insight detects the list of nutrients mentioned in a product, alongside their numeric value from the image OCR.
    nutrient = "nutrient"

    # The 'trace' insight detects traces that are present in the product from the image OCR.
    # NOTE: there are 0 insights of this type in the Postgres DB.
    trace = "trace"

    # The 'packaging' insight detects the type of packaging based on the image OCR.
    # This insight is always applied automatically.
    packaging = "packaging"

    # The 'location' insight detects the location of where the product comes from from the image OCR.
    # NOTE: there are 0 insights of this type in the Postgres DB.
    location = "location"

    # The 'nutrient_mention' insight detect mentions of nutrients from the image OCR (without actual values).
    nutrient_mention = "nutrient_mention"

    # The 'image_lang' insight detects which languages are mentioned on the product from the image OCR.
    image_lang = "image_lang"

    # The 'nutrition_image' insight tags images that have nutrition information based on the 'nutrient_mention' insight and the 'image_orientation' insight.
    # NOTE: this insight and the dependant insights has not been generated since 2020.
    nutrition_image = "nutrition_image"

    # The 'nutritional_table_structure' insight detects the nutritional table structure from the image.
    # NOTE: this insight has not been generated since 2020.
    nutrition_table_structure = "nutrition_table_structure"


@dataclasses.dataclass
class Insight:
    """This class is a copy of robotoff.models.ProductInsight - see that class's documentation field description."""

    barcode: str
    type: InsightType
    data: Dict[str, Any]
    latent: bool
    value_tag: Optional[str] = None
    value: Optional[str] = None
    automatic_processing: Optional[bool] = None
    source_image: Optional[str] = None
    reserved_barcode: bool = False
    server_domain: str = ""
    server_type: str = ""
    id: str = ""
    timestamp: Optional[datetime.datetime] = None
    process_after: Optional[datetime.datetime] = None
    predictor: Optional[str] = None
    countries: List[str] = dataclasses.field(default_factory=list)
    brands: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self, dict_factory=dict_factory)

    @classmethod
    def from_prediction(
        cls,
        prediction: "Prediction",
        product_predictions: "ProductPredictions",
        latent: bool,
    ) -> "Insight":
        return cls(
            latent=latent,
            type=InsightType(prediction.type),
            data=prediction.data,
            value_tag=prediction.value_tag,
            value=prediction.value,
            automatic_processing=prediction.automatic_processing,
            barcode=product_predictions.barcode,
            source_image=product_predictions.source_image,
            predictor=prediction.predictor,
        )


def dict_factory(*args, **kwargs):
    d = dict(*args, **kwargs)
    for key, value in d.items():
        if isinstance(value, InsightType):
            d[key] = value.name

    return d
