import csv

from robotoff import settings
from robotoff.insights.ocr.core import get_source
from robotoff.products import ProductDataset

ds = ProductDataset.load()

product_iter = (ds.stream()
                  .filter_by_country_tag('en:france')
                  .filter_nonempty_text_field('ingredients_text_fr')
                  .filter_number_field('unknown_ingredients_n', 2, 0, 'geq')
                  .iter())

with open('spellcheck_test_fr.csv', 'w', newline='') as f:
    writer = csv.writer(f, delimiter=',', dialect='unix')

    for product in product_iter:
        if 'images' not in product:
            continue

        images = product['images']

        if 'ingredients_fr' not in images:
            continue

        print(product['unknown_ingredients_n'])
        barcode = product['code']
        url = 'https://world.openfoodfacts.org/product/{}'.format(barcode)

        rev_id = nutrition_fr_image_url = images['ingredients_fr']['rev']
        image_name = "ingredients_fr.{}.400".format(rev_id)
        image_url = settings.OFF_IMAGE_BASE_URL + get_source(image_name, barcode=barcode)
        writer.writerow([barcode, url, image_url, product['ingredients_text_fr']])
