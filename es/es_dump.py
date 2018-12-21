import hashlib
import json
from typing import Dict, Iterable, Tuple

import argparse

from es.utils import get_es_client, ELASTIC_SEARCH_INDEX, ELASTIC_SEARCH_TYPE
from robotoff import utils

logger = utils.get_logger()


SUPPORTED_LANG = {
    'fr',
    'en',
    'es',
    'de',
}


def category_export(file_path):
    logger.info("Starting category export to Elasticsearch...")
    client = get_es_client()

    with open(str(file_path), 'r') as f:
        categories = json.load(f)

    rows_inserted = perform_category_export(client, categories)
    logger.info("%d rows inserted" % rows_inserted)


def perform_category_export(client,
                            categories: Dict[str, Dict],
                            batch_size=100):
    batch = []
    rows_inserted = 0

    for category_id, category_data in categories.items():
        category_names = category_data['name']

        supported_langs = [lang for lang in category_names
                           if lang in SUPPORTED_LANG]

        data = {
            f"{lang}:name": category_names[lang]
            for lang in supported_langs
        }
        data['id'] = category_id

        id_ = hashlib.sha256(category_id.encode('utf-8')).hexdigest()

        batch.append(
            (
                {
                    'index': {
                        '_id': id_
                    }
                },
                data
            )
        )

        if len(batch) >= batch_size:
            insert_batch(client, batch)
            rows_inserted += len(batch)
            batch = []

    if batch:
        insert_batch(client, batch)
        rows_inserted += len(batch)

    return rows_inserted


def insert_batch(client, batch: Iterable[Tuple[dict, dict]]):
    body = ""
    for action, source in batch:
        body += "{}\n{}\n".format(json.dumps(action),
                                  json.dumps(source))

    client.bulk(body=body,
                index=ELASTIC_SEARCH_INDEX,
                doc_type=ELASTIC_SEARCH_TYPE)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="file path of category taxonomy "
                                      "in JSON")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    category_export(args.input)
