import json
import argparse

from es.utils import get_es_client, ELASTIC_SEARCH_INDEX, ELASTIC_SEARCH_TYPE


def match(query: str):
    client = get_es_client()
    body = generate_request(query)
    results = client.search(index=ELASTIC_SEARCH_INDEX,
                            doc_type=ELASTIC_SEARCH_TYPE,
                            body=body,
                            _source=True)
    print(json.dumps(results['hits'], indent=4))


def generate_request(query: str):
    return {
        "query": {
            "match_phrase": {
                "fr:name": query
            }
        }
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="query to search")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    match(args.query)
