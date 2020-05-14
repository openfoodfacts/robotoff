import pytest
import itertools
import requests

from robotoff.utils.es import get_es_client
from robotoff.spellcheck.v2 import PipelineSpellchecker
from robotoff.spellcheck.v1.ingredients import (
    generate_corrections,
    generate_corrected_text,
)


es_client = get_es_client()
confidence = 1
index_name = "product"
spellchecker_v2 = PipelineSpellchecker()
spellchecker_v2.add_spellchecker(
    "elasticsearch", client=es_client, index_name=index_name, confidence=confidence,
)


def spellcheck_v1(text):
    corrections = generate_corrections(
        client=es_client,
        ingredients_text=text,
        confidence=confidence,
        index_name=index_name,
    )
    term_corrections = list(
        itertools.chain.from_iterable((c.term_corrections for c in corrections))
    )
    return generate_corrected_text(term_corrections, text) or text


def spellcheck_v2(text):
    return spellchecker_v2.correct(text)


@pytest.mark.parametrize(
    "url",
    [
        "https://raw.githubusercontent.com/openfoodfacts/openfoodfacts-ai/master/spellcheck/test_sets/fr/uniform_sampling/original.txt",
    ],
)
def test_consistency(url):
    with requests.get(url) as r:
        for line in r.text.splitlines():
            _, text = line.split("\t")
            correct_v1 = spellcheck_v1(text)
            correct_v2 = spellcheck_v2(text)
            assert correct_v1 == correct_v2
