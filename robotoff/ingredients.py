import operator
import re
from dataclasses import dataclass, field
from typing import List, Tuple, Iterable, Dict

from robotoff import settings
from robotoff.utils.es import get_es_client, generate_msearch_body

SPLITTER_CHAR = {'(', ')', ',', ';', '[', ']', '-', '{', '}'}

# Food additives (EXXX) may be mistaken from one another, because of their edit distance proximity
BLACKLIST_RE = re.compile(r"(?:\d+(?:,\d+)?\s*%)|(?:E\d{3})")


OffsetType = Tuple[int, int]


@dataclass
class Ingredients:
    text: str
    normalized: str
    offsets: List[OffsetType] = field(default_factory=list)

    def iter_normalized_ingredients(self):
        for start, end in self.offsets:
            yield self.normalized[start:end]

    def get_ingredient(self, index):
        start, end = self.offsets[index]
        return self.text[start:end]

    def get_normalized_ingredient(self, index):
        start, end = self.offsets[index]
        return self.normalized[start:end]

    def ingredient_count(self):
        return len(self.offsets)


@dataclass
class TermCorrection:
    original: str
    correction: str
    start_offset: int
    end_offset: int


@dataclass
class Correction:
    term_corrections: List[TermCorrection]
    score: int


def normalize_ingredients(ingredient_text: str):
    normalized = ingredient_text

    while True:
        try:
            match = next(BLACKLIST_RE.finditer(normalized))
        except StopIteration:
            break

        if match:
            start = match.start()
            end = match.end()
            normalized = normalized[:start] + ' ' * (end - start) + normalized[end:]
        else:
            break

    return normalized


def process_ingredients(ingredient_text: str):
    offsets = []
    chars = []

    normalized = normalize_ingredients(ingredient_text)
    start_idx = 0

    for idx, char in enumerate(normalized):
        if char in SPLITTER_CHAR:
            offsets.append((start_idx, idx))
            start_idx = idx + 1
            chars.append(' ')
        else:
            chars.append(char)

    if start_idx != len(normalized):
        offsets.append((start_idx, len(normalized)))

    normalized = ''.join(chars)
    return Ingredients(ingredient_text, normalized, offsets)


def generate_corrections(client, ingredients_text: str, **kwargs) -> List[Correction]:
    corrections = []
    ingredients = process_ingredients(ingredients_text)
    normalized_ingredients = ingredients.iter_normalized_ingredients()

    for idx, suggestions in enumerate(_suggest_batch(client, normalized_ingredients, **kwargs)):
        ingredient = ingredients.get_ingredient(idx)
        offsets = ingredients.offsets[idx]
        normalized_ingredient = ingredients.get_normalized_ingredient(idx)
        options = suggestions['options']

        if not options:
            continue

        option = options[0]
        original_tokens = analyze(client, normalized_ingredient)
        suggestion_tokens = analyze(client, option['text'])
        try:
            term_corrections = format_corrections(original_tokens,
                                                  suggestion_tokens,
                                                  offsets[0])
            corrections.append(Correction(term_corrections, option['score']))
        except ValueError:
            print("Mismatch")
            # Length mismatch exception
            continue

    return corrections


def generate_corrected_text(corrections: List[TermCorrection], text: str):
    sorted_corrections = sorted(corrections,
                                key=operator.attrgetter('start_offset'))
    corrected_fragments = []

    last_correction = None
    for correction in sorted_corrections:
        if last_correction is None:
            corrected_fragments.append(text[:correction.start_offset])
        else:
            corrected_fragments.append(
                text[last_correction.end_offset:correction.start_offset])

        corrected_fragments.append(correction.correction)
        last_correction = correction

    if last_correction is not None:
        corrected_fragments.append(text[last_correction.end_offset:])

    return ''.join(corrected_fragments)


def format_corrections(original_tokens: List[Dict],
                       suggestion_tokens: List[Dict],
                       offset: int=0):
    corrections = []

    if len(original_tokens) != len(suggestion_tokens):
        raise ValueError("The original text and the suggestions must have the same number of tokens")

    for original_token, suggestion_token in zip(original_tokens, suggestion_tokens):
        original_token_str = original_token['token']
        suggestion_token_str = suggestion_token['token']

        if original_token_str.lower() != suggestion_token_str:
            if original_token_str.isupper():
                token_str = suggestion_token_str.upper()
            elif original_token_str.istitle():
                token_str = suggestion_token_str.capitalize()
            else:
                token_str = suggestion_token_str

            token_start = original_token['start_offset']
            token_end = original_token['end_offset']
            corrections.append(TermCorrection(original=original_token_str,
                                              correction=token_str,
                                              start_offset=offset+token_start,
                                              end_offset=offset+token_end))

    return corrections


def _suggest(client, text):
    suggester_name = "autocorrect"
    body = generate_suggest_query(text, name=suggester_name)
    response = client.search(index='product',
                             doc_type='document',
                             body=body,
                             _source=False)
    return response['suggest'][suggester_name]


def analyze(client, ingredient_text: str):
    r = client.indices.analyze(index=settings.ELASTICSEARCH_PRODUCT_INDEX,
                               body={
                                   'tokenizer': "standard",
                                   'text': ingredient_text
                               })
    return r['tokens']


def _suggest_batch(client, texts: Iterable[str], **kwargs) -> List[Dict]:
    suggester_name = "autocorrect"
    queries = (generate_suggest_query(text, name=suggester_name, **kwargs)
               for text in texts)
    body = generate_msearch_body(settings.ELASTICSEARCH_PRODUCT_INDEX, queries)
    response = client.msearch(body=body,
                              doc_type=settings.ELASTICSEARCH_TYPE)

    suggestions = []

    for r in response['responses']:
        if r['status'] != 200:
            root_cause = response['error']['root_cause'][0]
            error_type = root_cause['type']
            error_reason = root_cause['reason']
            print("Elasticsearch error: {} [{}]"
                  "".format(error_reason, error_type))
            continue

        suggestions.append(r['suggest'][suggester_name][0])

    return suggestions


def generate_suggest_query(text,
                           confidence=1,
                           size=1,
                           min_word_length=4,
                           suggest_mode="popular",
                           name="autocorrect"):
    return {
        "suggest": {
            "text": text,
            name: {
                "phrase": {
                    "confidence": confidence,
                    "field": "ingredients_text_fr.trigram",
                    "size": size,
                    "gram_size": 3,
                    "direct_generator": [
                        {
                            "field": "ingredients_text_fr.trigram",
                            "suggest_mode": suggest_mode,
                            "min_word_length": min_word_length
                        }
                    ]
                }
            }
        }
    }


if __name__ == "__main__":
    client = get_es_client()
    # r = _suggest_batch(client, ["Fromage  blcnc allégé", "fruits & sucralose", "Huile  d'oluve"])
    # print(r)
    # suggest(client, "huile de colza 15,6%, gras de porn, huile de morie")
    # print(analyze(client, "Huile  d\"olive"))
    # text = "Fromage  Blcnc allégé 10,5%, fruits & sucralose, Huile  d'oluve"
    text = """Garniture 57,4 % : préparation de viande bovine hachée cuite* 42,9 % (viande bovine origine France, sel, arômes), cheddar 21,4 % (lait de vache pasteurisé, sel, ferments lactiques, coagulant, colorant : E160b), sauce ketchup (tomate, sirop de glucose et fructose, sucre, vinaigre d'alcool, amidon modifié de maïs, sel, arôme, conservateurs : E202, E211), bacon* 10,7 % (maigre de porc, sel, dextrose de blé, arôme de fumée, acidifiant : E330, conservateurs : E316, E250), cornichons, 7,1 %,(cornichons, eau, vinaigre d'alcool, sel, conservateurs : E224). Pourcentages exprimés sur la garniture. Pain spécial* 42,6 % : farine de blé, eau, sucre, levure, huile de colza, graines de sésame, dextrose de blé, sel, conservateur : E282, émulsifiants : E471, E472e, agent de traitement de la farine : E300. * Ingrédients décongelés, ne pas congeler ce produit."""
    # text = """légumes 65% (jus de tomate reconstilué 48%, oignon 5,8%, pois chiche cuit 5,6%, céleril, eau, lentille verte cuite 5,6%, huile d'olive, amidon transformé de mais, sel, persil 0,6%, coriandre 0,6%, arômes, piment 0,01% Traces possibles de lait, crustacé poissons, mollusques, moutarde, gluten, ceuf, soja et fruits à coque"""
    text = """farine de blé - viande de dinde 21,6% eau viande de porc 6,7% - beurre-gras de porc foie de porc - brandy - pistaches-sel - fécule dextrose gélatine de porc tissu conjonctif de porc - épices et plantes aromatiques vin arômes naturels vin aromatisé eufs entiers-colorants : E160a, E150a gélifiant E407 antioxydant E301 lactose - acidifiant E330 conservateur E250 Traces de fruits à coques, moutarde.soja céleri et poissons Dinde et viande de porc origine: UE Les informations en gras sont destinées aux personnes intolérantes ou allergiques. CONSEIL D'UTILISATION pour plus de saveur, sortez le produit de son emballage 15 minutes avant de servir. CONSERVATION CONDITIONS DE"""
    corrections = generate_corrections(client, text, confidence=1)
    print(corrections)
