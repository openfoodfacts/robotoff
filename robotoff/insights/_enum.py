from enum import Enum, unique


class StrEnum(str, Enum):
    pass


@unique
class InsightType(StrEnum):
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
    packaging = "packaging"
    location = "location"
    nutrient_mention = "nutrient_mention"
    image_lang = "image_lang"
    nutrition_image = "nutrition_image"
