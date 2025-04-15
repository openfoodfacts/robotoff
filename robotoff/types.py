import dataclasses
import datetime
import enum
import uuid
from collections import Counter
from typing import Any, Literal, Optional, Self

from pydantic import BaseModel, model_validator

#: A precise expectation of what mappings looks like in json.
#: (dict where keys are always of type `str`).
JSONType = dict[str, Any]


class ObjectDetectionModel(str, enum.Enum):
    nutriscore = "nutriscore"
    universal_logo_detector = "universal_logo_detector"
    nutrition_table = "nutrition_table"
    price_tag_detection = "price_tag_detection"


class ImageClassificationModel(str, enum.Enum):
    price_proof_classification = enum.auto()


@enum.unique
class NeuralCategoryClassifierModel(enum.Enum):
    keras_image_embeddings_3_0 = "keras-image-embeddings-3.0"


@enum.unique
class PredictionType(str, enum.Enum):
    """PredictionType defines the type of the prediction.

    See `InsightType` documentation for further information about each type.
    """

    ingredient_spellcheck = "ingredient_spellcheck"
    packager_code = "packager_code"
    label = "label"
    category = "category"
    image_flag = "image_flag"
    product_weight = "product_weight"
    expiration_date = "expiration_date"
    brand = "brand"
    image_orientation = "image_orientation"
    store = "store"
    nutrient = "nutrient"
    trace = "trace"
    packaging_text = "packaging_text"
    packaging = "packaging"
    location = "location"
    nutrient_mention = "nutrient_mention"
    image_lang = "image_lang"
    nutrition_image = "nutrition_image"
    is_upc_image = "is_upc_image"
    nutrient_extraction = "nutrient_extraction"


@enum.unique
class InsightType(str, enum.Enum):
    """InsightType defines the type of the insight."""

    # The 'ingredient spellcheck' insight corrects the spelling in the given
    # ingredients list.
    ingredient_spellcheck = "ingredient_spellcheck"

    # The 'packager code' insight extracts the packager code using regex from
    # the image OCR. This insight is always applied automatically.
    packager_code = "packager_code"

    # The 'label' insight predicts a label that appears on the product
    #  packaging photo. Several labels are possible:
    #   - Nutriscore label detection.
    #   - Logo detection using the universal logo detector.
    #   - OCR labeling based on text parsing.
    label = "label"

    # The 'category' insight predicts the category of a product.
    # This insight can be generated by 2 different predictors:
    #  1. The Keras ML category classifier.
    #  2. The Elasticsearch category predictor based on product name.
    #
    # NOTE: there also exists a hierachical category classifier, but it hasn't
    # generated any insights since 2019.
    category = "category"

    # The 'image_flag' insight flags inappropriate images based on OCR text.
    # This insight type is never persisted to the Postgres DB and is only used
    # to pass insight information in memory.
    #
    # Currently 3 possible sources of flagged images are possible:
    #  1) "safe_search_annotation" - Google's SafeSearch API detects explicit
    #     content on product images.
    #  2) "label_annotation" - a list of hard-coded labels that should be
    #     flagged that are found on the image's OCR.
    #  3) Flashtext matches on the image's OCR.
    image_flag = "image_flag"

    # The 'product_weight' insight extracts the product weight from the image
    # OCR. This insight is never applied automatically.
    product_weight = "product_weight"

    # The 'expiration_date' insight extracts the expiration date from the image
    # OCR.
    expiration_date = "expiration_date"

    # The 'brand' insight extracts the product's brand from the image OCR.
    brand = "brand"

    # The 'image_orientation' insight predicts the image orientation of the
    # given image.
    image_orientation = "image_orientation"

    # The 'store' insight detects the store where the given product is sold
    # from the image OCR.
    store = "store"

    # The 'nutrient' insight detects the list of nutrients mentioned in a
    # product, alongside their numeric value from the image OCR.
    nutrient = "nutrient"

    # The 'trace' insight detects traces that are present in the product from
    # the image OCR. NOTE: there are 0 insights of this type in the Postgres
    # DB.
    trace = "trace"

    # (legacy) The 'packaging_text' insight detects the type of packaging based
    # on the image OCR. This type used to be named 'packaging' and has been
    # renamed into `packaging_text`, so that 'packaging' type can be used for
    # detections of detailed packaging information (shape, material,...). This
    # insight used to be applied automatically.
    packaging_text = "packaging_text"

    # The 'packaging' insight detects the type of packaging based on the image
    # OCR. The details about each packaging element (shape, material,
    # recycling) is returned.
    packaging = "packaging"

    # The 'location' insight detects the location of where the product comes
    # from from the image OCR. NOTE: there are 0 insights of this type in the
    # Postgres DB.
    location = "location"

    # The 'nutrient_mention' insight detect mentions of nutrients from the
    # image OCR (without actual values).
    nutrient_mention = "nutrient_mention"

    # The 'image_lang' insight detects which languages are mentioned on the
    # product from the image OCR.
    image_lang = "image_lang"

    # The 'nutrition_image' insight predicts the nutrition image for the
    # product main language.
    nutrition_image = "nutrition_image"

    # The 'is_upc_image' insight predicts whether or not the image is largely
    # dominated by a UPC (barcode)
    is_upc_image = "is_upc_image"

    # Nutrient values extracted from images
    nutrient_extraction = "nutrient_extraction"


class ServerType(str, enum.Enum):
    """ServerType is used to refer to a specific Open*Facts project:

    - Open Food Facts
    - Open Beauty Facts
    - Open Pet Food Facts
    - Open Product Facts
    - Open Food Facts (Pro plateform)
    """

    off = "off"
    obf = "obf"
    opff = "opff"
    opf = "opf"
    off_pro = "off-pro"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    def get_base_domain(self) -> str:
        """Get the base domain (domain without TLD and without world/api
        subdomain) associated with the `ServerType`."""
        if self == self.off:
            return "openfoodfacts"
        elif self == self.obf:
            return "openbeautyfacts"
        elif self == self.opff:
            return "openpetfoodfacts"
        elif self == self.opf:
            return "openproductfacts"
        else:
            # Open Food Facts Pro
            return "pro.openfoodfacts"

    @classmethod
    def from_product_type(cls, product_type: str) -> "ServerType":
        """Get the `ServerType` associated with a product type."""
        if product_type == "food":
            return cls.off
        elif product_type == "beauty":
            return cls.obf
        elif product_type == "petfood":
            return cls.opff
        elif product_type == "product":
            return cls.opf
        raise ValueError(f"no ServerType matched for product_type {product_type}")

    @classmethod
    def get_from_server_domain(cls, server_domain: str) -> "ServerType":
        """Get the `ServerType` associated with a `server_domain`."""
        subdomain, base_domain, tld = server_domain.rsplit(".", maxsplit=2)

        if subdomain == "api.pro":
            if base_domain == "openfoodfacts":
                return cls.off_pro
            raise ValueError("pro platform is only available for Open Food Facts")

        for server_type in cls:
            if base_domain == server_type.get_base_domain():
                return server_type

        raise ValueError(f"no ServerType matched for server_domain {server_domain}")

    def is_food(self) -> bool:
        """Return True if the server type is `off` or `off-pro`, False
        otherwise."""
        return self in (self.off, self.off_pro)


@dataclasses.dataclass
class Prediction:
    type: PredictionType
    data: dict[str, Any] = dataclasses.field(default_factory=dict)
    value_tag: Optional[str] = None
    value: Optional[str] = None
    automatic_processing: Optional[bool] = None
    predictor: Optional[str] = None
    predictor_version: Optional[str] = None
    barcode: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    source_image: Optional[str] = None
    id: Optional[int] = None
    confidence: Optional[float] = None
    server_type: ServerType = ServerType.off

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self, dict_factory=dict_factory)


def dict_factory(*args, **kwargs):
    d = dict(*args, **kwargs)
    for key, value in d.items():
        if isinstance(value, (PredictionType, ServerType)):
            d[key] = value.name

    return d


@dataclasses.dataclass
class ProductIdentifier:
    """Dataclass to uniquely identify a product across all Open*Facts
    projects, with:

    - the product barcode: for the pro platform, it must be in the format
      `{ORG_ID}/{BARCODE}` (ex: `org-lea-nature/3307130803004`), otherwise it's
      the barcode only
    - the project specified by the ServerType
    """

    barcode: str
    server_type: ServerType

    def __repr__(self) -> str:
        return "<Product %s | %s>" % (self.barcode, self.server_type.name)

    def __hash__(self) -> int:
        return hash((self.barcode, self.server_type))

    def is_valid(self) -> bool:
        return bool(self.barcode and self.server_type)


@enum.unique
class ElasticSearchIndex(str, enum.Enum):
    logo = "logo"


@dataclasses.dataclass
class ProductInsightImportResult:
    insight_created_ids: list[uuid.UUID]
    insight_updated_ids: list[uuid.UUID]
    insight_deleted_ids: list[uuid.UUID]
    product_id: ProductIdentifier
    type: InsightType


@dataclasses.dataclass
class PredictionImportResult:
    created: int
    deleted: int
    barcode: str
    server_type: ServerType


@dataclasses.dataclass
class InsightImportResult:
    product_insight_import_results: list[ProductInsightImportResult] = (
        dataclasses.field(default_factory=list)
    )
    prediction_import_results: list[PredictionImportResult] = dataclasses.field(
        default_factory=list
    )

    def created_predictions_count(self) -> int:
        return sum(x.created for x in self.prediction_import_results)

    def deleted_predictions_count(self) -> int:
        return sum(x.deleted for x in self.prediction_import_results)

    def created_insights_count(self) -> int:
        return sum(
            len(x.insight_created_ids) for x in self.product_insight_import_results
        )

    def deleted_insights_count(self) -> int:
        return sum(
            len(x.insight_deleted_ids) for x in self.product_insight_import_results
        )

    def updated_insights_count(self) -> int:
        return sum(
            len(x.insight_updated_ids) for x in self.product_insight_import_results
        )

    def __repr__(self) -> str:
        return (
            f"<InsightImportResult insights: created={self.created_insights_count()}, "
            f"updated={self.updated_insights_count()}, "
            f"deleted={self.deleted_insights_count()}, "
            f"types: {list(set(result.type.value for result in self.product_insight_import_results))}, "
            f"predictions: created={self.created_predictions_count()}, "
            f"deleted={self.deleted_predictions_count()}>"
        )


@enum.unique
class PackagingElementProperty(enum.Enum):
    shape = "shape"
    material = "material"
    recycling = "recycling"


LogoLabelType = tuple[str, Optional[str]]

InsightAnnotation = Literal[-1, 0, 1, 2]


@enum.unique
class BatchJobType(enum.Enum):
    """Each job type correspond to a task that will be executed in the batch job."""

    ingredients_spellcheck = "ingredients-spellcheck"


class NutrientSingleValue(BaseModel):
    value: str
    unit: str | None = None


class NutrientData(BaseModel):
    nutrients: dict[str, NutrientSingleValue]
    serving_size: str | None = None
    nutrition_data_per: Literal["100g", "serving"] | None = None

    @model_validator(mode="before")
    @classmethod
    def move_fields(cls, data: Any) -> Any:
        if isinstance(data, dict) and "nutrients" in data:
            if "serving_size" in data["nutrients"]:
                # In the input data, `serving_size` is a key of the `nutrients`
                # while on Product Opener, it's a different field. We move it
                # to the root of the dict to be compliant with Product Opener
                # API.
                serving_size = data["nutrients"].pop("serving_size")
                if isinstance(serving_size, dict):
                    data["serving_size"] = serving_size["value"]
                else:
                    data["serving_size"] = serving_size
        return data

    @model_validator(mode="after")
    def validate_nutrients(self) -> Self:
        if len(self.nutrients) == 0:
            raise ValueError("at least one nutrient is required")

        # We expect all nutrient keys to be in the format `{nutrient_name}_{unit}`
        # where `unit` is either `100g` or `serving`.
        if not all("_" in k for k in self.nutrients):
            raise ValueError("each nutrient key must end with '_100g' or '_serving'")

        # We select the as `nutrition_data_per` the most common value between `100g`
        # and `serving`.
        # When the data is submitted by the client, we expect all nutrient keys to
        # have the same unit (either `100g` or `serving`).
        # When the annotation is performed directly from the insight (without user
        # update or validation), we select the most common key.
        nutrition_data_per_count = Counter(
            key.rsplit("_", maxsplit=1)[1] for key in self.nutrients.keys()
        )
        if set(nutrition_data_per_count.keys()).difference({"100g", "serving"}):
            # Some keys are not ending with '_100g' or '_serving'
            raise ValueError("each nutrient key must end with '_100g' or '_serving'")

        # Select the most common nutrition data per
        self.nutrition_data_per = nutrition_data_per_count.most_common(1)[0][0]  # type: ignore
        self.nutrients = {
            k.rsplit("_", maxsplit=1)[0]: v
            for k, v in self.nutrients.items()
            if k.endswith(self.nutrition_data_per)  # type: ignore
        }
        return self


class ImportImageFlag(str, enum.Enum):
    add_image_fingerprint = "add_image_fingerprint"
    import_insights_from_image = "import_insights_from_image"
    extract_ingredients = "extract_ingredients"
    extract_nutrition = "extract_nutrition"
    run_logo_object_detection = "run_logo_object_detection"
    run_nutrition_table_object_detection = "run_nutrition_table_object_detection"
