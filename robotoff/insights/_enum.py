from enum import Enum, unique


@unique
class InsightType(Enum):
    ingredient_spellcheck = 1
    packager_code = 2
    label = 3
    category = 4
    image_flag = 5
    product_weight = 6
    expiration_date = 7
    brand = 8
    image_orientation = 9
    store = 10
    nutrient = 11
    trace = 12
    packaging = 13
    location = 14
    nutrient_mention = 15
    image_lang = 16
    nutrition_image = 17
