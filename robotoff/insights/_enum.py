from enum import Enum, unique


class StrEnum(str, Enum):
    pass


@unique
class InsightType(StrEnum):
    # The 'ingredient spellcheck' insight corrects the spelling in the given ingredients list.
    # Current limitations are:
    #  - Spellchecking only works for French text.
    #  - Spellchecking is only set to generate insights - but these are not surfaced/applied - TODO(kulizhsy): validate this comment.
    ingredient_spellcheck = "ingredient_spellcheck"

    # The 'packager code' insight extracts the packager code using regex for the product from the image OCR.
    packager_code = "packager_code"

    # The 'label' insight predicts a label that appears on the product packaging photo.
    label = "label"

    # The 'category' insight predicts the category of a product either using ElasticSearch or an ML model.
    category = "category"

    # The 'image_flag' insight flags inappropriate images based on OCR text.
    # TODO(kulizhsy): there are currently 0 insights of this type in the Postgres DB.
    image_flag = "image_flag"

    # The 'product_weight' insight extracts the product weight from the image OCR.
    product_weight = "product_weight"

    # The 'expiration_date' insight extracts the expiration date from the image OCR.
    expiration_date = "expiration_date"

    # The 'brand' insight extracts the product's brand from the image OCR.
    brand = "brand"

    # The 'image_orientation' insight predicts the image orientation of the given image.
    # TODO(kulizhsy): currently there are 0 insights of this type in the Postgres DB.
    image_orientation = "image_orientation"

    # The 'store' insight detects the store where the given product is sold from the image OCR.
    store = "store"

    # The 'nutrient' insight detects the list of nutrients mentioned in a product from the image OCR.
    # TODO(kulizhsy): there are 0 insights of this type in the Postgres DB.
    nutrient = "nutrient"

    # The 'trace' insight detects traces that are present in the product from the image OCR.
    # TODO(kulizhsy): there are 0 insights of this type in the Postgres DB.
    trace = "trace"

    # The 'packaging' insight detects the type of packaging based on the image OCR.
    # TODO(kulizhsy): there are 0 insights of this type in the Postgres DB.
    packaging = "packaging"

    # The 'location' insight detects the location of where the product comes from from the image OCR.
    # TODO(kulizhsy): there are 0 insights of this type in the Postgres DB.
    location = "location"

    # The 'nutrient_mention' insight detect mentions of nutrients from the image OCR.
    # TODO(kulizhsy): there are 0 insights of this type in the Postgres DB.
    # TODO(kulizhsy): can this be merged with the 'nutrient' insight above?
    nutrient_mention = "nutrient_mention"

    # The 'image_lang' insight detects which languages are mentioned on the product from the image OCR.
    # TODO(kulizhsy): there are 0 insights of this type in the Postgres DB.
    image_lang = "image_lang"

    # The 'nutrition_image' insight tags images that have nutrition information based on the 'nutrient_mention' insight and the 'image_orientation' insight.
    # TODO(kulizhsy): check how this should work?
    nutrition_image = "nutrition_image"

    # The 'nutritional_table_structure' insight detects the nutritional table structure from the image.
    # TODO(kulizhsy): this doesn't seem to be working at all?
    nutrition_table_structure = "nutrition_table_structure"


# TODO(kulizhsy): figure out why so many insights have null values for 'process_after', 'latent', 'annotation', 'automatic_processing', sample IDs:
#
# 12699561-0d3c-43a3-967a-e035d5557fd7
# 6c5884a2-2a14-403b-8468-5b195b1a8cde
# 2086ca3e-bc89-4179-b706-33214a3c1385
# 7c01686a-aa42-472a-97d5-2b9d7ce25eae

# https://robotoff.openfoodfacts.org/api/v1/insights/detail/{id}

# TODO(kulizhsy): validate which insight types work correctly and what the average accuracy is: e.g. how many are currently working etc.

# TODO(kulizhsy): verify why we have local taxonomies as opposed to getting them from Product Opener directly.

# TODO(kulizhsy): figure out how generate_nutrition_image_insights works when it relies on the 'image_orientation' insight.
