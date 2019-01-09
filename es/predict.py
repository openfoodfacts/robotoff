import operator
from typing import Iterable

from robotoff.products import ProductDataset
from robotoff import settings
from robotoff.utils import dump_jsonl

from robotoff.utils import get_es_client
from es.match import predict_category


def generate_dataset(client, products: Iterable[dict]) -> Iterable[dict]:
    for product in products:
        predictions = []

        for lang in product['languages_codes']:
            product_name = product.get(f"product_name_{lang}")

            if not product_name:
                continue

            prediction = predict_category(client, product_name, lang)

            if prediction is None:
                continue

            category, score = prediction
            predictions.append((lang, category, score))
            continue

        if predictions:
            # Sort by descending score
            sorted_predictions = sorted(predictions,
                                        key=operator.itemgetter(2),
                                        reverse=True)

            prediction = sorted_predictions[0]
            lang, category, score = prediction

            yield {
                'predicted_category_tag': category,
                'predicted_category_lang': lang,
                'code': product['code'],
                'last_modified_t': product['last_modified_t'],
                'countries_tags': product['countries_tags'],
            }


dataset = ProductDataset(settings.JSONL_DATASET_PATH)

product_iter = (dataset.stream()
                       .filter_nonempty_text_field('product_name')
                       .filter_empty_tag_field('categories_tags')
                       .filter_nonempty_tag_field('countries_tags')
                       .filter_nonempty_tag_field('languages_codes')
                       .iter())

print("Performing prediction on products without categories")

es_client = get_es_client()
prediction_dataset = generate_dataset(es_client, product_iter)
dump_jsonl('predicted_categories_matcher.json', prediction_dataset)
