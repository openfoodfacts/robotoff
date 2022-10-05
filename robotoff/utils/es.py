import json
from typing import Dict, Iterable, Tuple

import elasticsearch

from robotoff import settings


def get_es_client():
    return elasticsearch.Elasticsearch(settings.ELASTICSEARCH_HOSTS)


def perform_export(
    client, data: Iterable[Tuple[str, Dict]], index: str, batch_size=100
) -> int:
    batch = []
    rows_inserted = 0

    for id_, item in data:
        batch.append(({"index": {"_id": id_}}, item))

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
        body += "{}\n{}\n".format(json.dumps(action), json.dumps(source))

    client.bulk(body=body, index=index, doc_type=settings.ELASTICSEARCH_TYPE)


def generate_msearch_body(index: str, queries: Iterable[Dict]):
    lines = []

    for query in queries:
        lines.append(json.dumps({"index": index}))
        lines.append(json.dumps(query))

    return "\n".join(lines)
