from enum import Enum


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
