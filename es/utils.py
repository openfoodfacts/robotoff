import json
from typing import Iterable, Dict, Tuple

import elasticsearch

ELASTIC_SEARCH_HOST = "localhost:9200"
ELASTIC_SEARCH_TYPE = "document"


def get_es_client():
    return elasticsearch.Elasticsearch(ELASTIC_SEARCH_HOST)


def perform_export(client,
                   data: Iterable[Tuple[str, Dict]],
                   index: str,
                   batch_size=100):
    batch = []
    rows_inserted = 0

    for id_, item in data:
        batch.append(
            (
                {
                    'index': {
                        '_id': id_
                    }
                },
                item
            )
        )

        if len(batch) >= batch_size:
            insert_batch(client, batch, index)
            rows_inserted += len(batch)
            batch = []

    if batch:
        insert_batch(client, batch, index)
        rows_inserted += len(batch)

    return rows_inserted


def insert_batch(client, batch: Iterable[Tuple[Dict, Dict]], index: str):
    body = ""
    for action, source in batch:
        body += "{}\n{}\n".format(json.dumps(action),
                                  json.dumps(source))

    client.bulk(body=body,
                index=index,
                doc_type=ELASTIC_SEARCH_TYPE)
