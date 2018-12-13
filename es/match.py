import json
import argparse
from typing import Union, Tuple

from es.utils import get_es_client, ELASTIC_SEARCH_INDEX, ELASTIC_SEARCH_TYPE


def predict_category(client, name: str) -> Union[None, Tuple[str, float]]:
    results = match(client, name)

    hits = results['hits']['hits']

    if hits:
        hit = hits[0]
        return hit['_source']['id'], hit['_score']


def match(client, query: str):
    body = generate_request(query)
    return client.search(index=ELASTIC_SEARCH_INDEX,
                         doc_type=ELASTIC_SEARCH_TYPE,
                         body=body,
                         _source=True)


def generate_request(query: str):
    return {
        "query": {
            "bool": {
                "should": [
                    {
                        "match_phrase": {
                            "fr:name": query
                        }
                    },
                    {
                        "match_phrase": {
                            "fr:name.stemmed": query
                        }
                    }
                ],
                "filter": [
                    {
                        "match_phrase": {
                            "fr:name.stemmed": query
                        }
                    }
                ]
            }
        }
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="query to search")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    es_client = get_es_client()
    results = match(es_client, args.query)
    print(json.dumps(results['hits'], indent=4))
