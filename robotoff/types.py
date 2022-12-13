import enum


class WorkerQueue(enum.Enum):
    robotoff_high = "robotoff-high"
    robotoff_low = "robotoff-low"


class ObjectDetectionModel(enum.Enum):
    nutriscore = "nutriscore"
    universal_logo_detector = "universal-logo-detector"
    nutrition_table = "nutrition-table"


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
    nutrition_table_structure = "nutrition_table_structure"
