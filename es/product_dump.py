import hashlib

from robotoff.products import ProductDataset
from robotoff import settings

from es.utils import get_es_client, perform_export

dataset = ProductDataset(settings.JSONL_DATASET_PATH)

product_iter = (dataset.stream()
                       .filter_by_country_tag('en:france')
                       .filter_nonempty_text_field('ingredients_text_fr')
                       .filter_by_state_tag('en:complete')
                       .iter())
data = ((hashlib.sha256(product['code'].encode('utf-8')).hexdigest(),
         {'ingredients_text_fr': product['ingredients_text_fr']})
        for product in product_iter)

print("Importing products")

es_client = get_es_client()
perform_export(es_client, data, 'product')
