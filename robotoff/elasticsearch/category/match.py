import json
import argparse
from typing import Tuple, Optional

from robotoff.elasticsearch.category.preprocessing import preprocess_name
from robotoff.utils.es import get_es_client
from robotoff import settings

SUPPORTED_LANG = {
    'fr',
    'en',
    'es',
    'de',
}


def predict_category(client, name: str, lang: str) -> Optional[Tuple[str, float]]:
    if lang not in SUPPORTED_LANG:
        return None

    preprocessed_name = preprocess_name(name, lang)
    results = match(client, preprocessed_name, lang)

    hits = results['hits']['hits']

    if hits:
        hit = hits[0]
        return hit['_source']['id'], hit['_score']
    
    return None


def match(client, query: str, lang: str):
    body = generate_request(query, lang)
    return client.search(index=settings.ELASTICSEARCH_CATEGORY_INDEX,
                         doc_type=settings.ELASTICSEARCH_TYPE,
                         body=body,
                         _source=True)


def generate_request(query: str, lang: str):
    return {
        "query": {
            "match_phrase": {
                "{}:name.stemmed".format(lang): {
                    "query": query,
                }
            }
        }
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="query to search")
    parser.add_argument("--lang", help="language of the query", default='fr')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    es_client = get_es_client()
    results = match(es_client, args.query, args.lang)
    print(json.dumps(results['hits'], indent=4))
