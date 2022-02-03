import argparse
import json
from typing import Optional, Tuple

from robotoff import settings
from robotoff.elasticsearch.category.preprocessing import preprocess_name
from robotoff.utils.es import get_es_client

SUPPORTED_LANG = {
    "fr",
    "en",
    "es",
    "de",
}


def predict_category(client, name: str, lang: str) -> Optional[Tuple[str, float]]:
    """Predict category from product name using ES.

    Lang is not used to filter category index, but to stem the name in the right way.

    :param elasticsearch.Elasticsearch client: ES client
    :param name: name of the product
    :param lang: language of the name

    :return: None if language not supported or no guess
    """
    if lang not in SUPPORTED_LANG:
        return None

    preprocessed_name = preprocess_name(name, lang)
    results = match(client, preprocessed_name, lang)

    hits = results["hits"]["hits"]

    if hits:
        hit = hits[0]
        return hit["_source"]["id"], hit["_score"]

    return None


def match(client, query: str, lang: str):
    """Match a phrase (query) against product database using stemming"""
    body = generate_request(query, lang)
    return client.search(
        index=settings.ElasticsearchIndex.CATEGORY,
        doc_type=settings.ELASTICSEARCH_TYPE,
        body=body,
        _source=True,
    )


def generate_request(query: str, lang: str):
    return {
        "query": {"match_phrase": {"{}:name.stemmed".format(lang): {"query": query}}}
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="query to search")
    parser.add_argument("--lang", help="language of the query", default="fr")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    es_client = get_es_client()
    results = match(es_client, args.query, args.lang)
    print(json.dumps(results["hits"], indent=4))
