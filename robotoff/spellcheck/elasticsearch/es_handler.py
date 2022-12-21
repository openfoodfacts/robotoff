import json
from typing import Iterable

from robotoff.types import ElasticSearchIndex


class ElasticsearchHandler:
    def __init__(
        self,
        client,
        confidence: float = 1.0,
        size: int = 1,
        min_word_length: int = 4,
        suggest_mode: str = "missing",
        suggester_name: str = "autocorrect",
        reverse: bool = True,
        index_name: str = ElasticSearchIndex.product,
    ):
        self.client = client
        self.confidence = confidence
        self.size = size
        self.min_word_length = min_word_length
        self.suggest_mode = suggest_mode
        self.suggester_name = suggester_name
        self.reverse = reverse
        self.index_name = index_name

    def analyze(self, text: str):
        return self.client.indices.analyze(
            index=self.index_name,
            body={"tokenizer": "standard", "text": text},
        )["tokens"]

    def suggest(self, text: str) -> dict:
        return self.suggest_batch([text])[0]

    def suggest_batch(self, texts: Iterable[str]) -> list[dict]:
        queries = [self.__generate_query(text) for text in texts]
        body = generate_msearch_body(self.index_name, queries)
        response = self.client.msearch(body=body)
        suggestions = self.__postprocess_response(response)
        return suggestions

    def __generate_query(self, text):
        direct_generators = [
            {
                "field": "ingredients_text_fr.trigram",
                "suggest_mode": self.suggest_mode,
                "min_word_length": self.min_word_length,
            }
        ]

        if self.reverse:
            direct_generators.append(
                {
                    "field": "ingredients_text_fr.reverse",
                    "suggest_mode": self.suggest_mode,
                    "min_word_length": self.min_word_length,
                    "pre_filter": "reverse",
                    "post_filter": "reverse",
                },
            )
        return {
            "suggest": {
                "text": text,
                self.suggester_name: {
                    "phrase": {
                        "confidence": self.confidence,
                        "field": "ingredients_text_fr.trigram",
                        "size": self.size,
                        "gram_size": 3,
                        "direct_generator": direct_generators,
                        "smoothing": {"laplace": {"alpha": 0.5}},
                    }
                },
            }
        }

    def __postprocess_response(self, response):
        suggestions = []
        for r in response["responses"]:
            if r["status"] != 200:
                root_cause = r["error"]["root_cause"][0]
                error_type = root_cause["type"]
                error_reason = root_cause["reason"]
                print(f"Elasticsearch error: {error_reason} [{error_type}]")
                continue
            suggestions.append(r["suggest"][self.suggester_name][0])
        return suggestions


def generate_msearch_body(index: str, queries: Iterable[dict]):
    lines = []

    for query in queries:
        lines.append(json.dumps({"index": index}))
        lines.append(json.dumps(query))

    return "\n".join(lines)
