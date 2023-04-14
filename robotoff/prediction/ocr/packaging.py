import functools
from typing import Optional, Union

from lark import Discard, Lark, Transformer

from robotoff import settings
from robotoff.prediction.ocr.dataclass import OCRResult, get_text
from robotoff.prediction.ocr.grammar import (
    generate_terminal_symbols_file,
    normalize_string,
)
from robotoff.taxonomy import TaxonomyType
from robotoff.types import PackagingElementProperty, Prediction, PredictionType
from robotoff.utils import get_logger, load_json
from robotoff.utils.text import strip_consecutive_spaces

logger = get_logger(__name__)

# Set of shapes to exclude when the material or recycling instructions were
# not detected along the shape
# Avoid many false positive
SHAPE_ONLY_EXCLUDE_SET = {
    "en:tray",  # coque
    "en:packaging",  # emballage
    "en:backing",  # plaque
    "en:packet",  # pack
    "en:string",  # ficelle
    "en:bowl",  # bol
    "en:sheet",  # feuilles
    "en:net",  # filet
    "en:pouch-flask",  # pouch, english word
    "en:spoon",  # most of the spoon are false positive
    "en:tablespoon",
    "en:mold",  # moule
    None,
}


def generate_packaging_lark_file(lang: str):
    """Generate the list of terminal symbols corresponding to taxonomies.

    File for recycling instruction terminal symbol was generated
    semi-automatically, as some fixes were required.
    """
    generate_terminal_symbols_file(
        output_path=settings.GRAMMARS_DIR / f"terminal_packaging_shape_{lang}.lark",
        lang=lang,
        terminal_name="PACKAGING_SHAPES",
        taxonomy_type=TaxonomyType.packaging_shape,
        terminal_priority=1,
        ignore_ids={"en:unknown"},
    )
    generate_terminal_symbols_file(
        output_path=settings.GRAMMARS_DIR / f"terminal_packaging_material_{lang}.lark",
        lang=lang,
        terminal_name="PACKAGING_MATERIALS",
        taxonomy_type=TaxonomyType.packaging_material,
        terminal_priority=1,
        ignore_ids={"en:unknown"},
    )


@functools.cache
def load_grammar(lang: str, start: str = "value", **kwargs) -> Lark:
    return Lark.open(
        str(settings.GRAMMARS_DIR / f"packaging_{lang}.lark"),
        start=start,
        **kwargs,
    )


class PackagingFRTransformer(Transformer):
    """For each processed rule, lark will call corresponding transformer
    method with items composing it as parameters (which maybe themselves the
    result of previous rules).
    """

    def __init__(
        self,
        taxonomy_maps: dict[str, dict[str, list[str]]],
        visit_tokens: bool = True,
    ) -> None:
        super().__init__(visit_tokens)
        self.taxonomy_maps = taxonomy_maps

    def value(self, items: list):
        return items

    def packaging(self, items: list):
        data = {}
        for item in items:
            data.update(item)
        return data

    def to_recycling(self, items: list):
        return items[-1]

    def shape_material(self, items: list):
        shape, *material = items

        if len(material) == 1:
            material = material[0]
        else:
            # 2 items, "plastique PET", only keep the last one
            material = material[1]
        return {**shape, **material}

    def WS(self, token):
        return Discard

    def OTHER(self, token):
        return Discard

    def PACKAGING_RECYCLING(self, token):
        return {
            "recycling": {
                "value": token.value,
                "value_tag": self._match_tag(
                    TaxonomyType.packaging_recycling.name, token.value
                ),
            }
        }

    def PACKAGING_SHAPES(self, token):
        return {
            "shape": {
                "value": token.value,
                "value_tag": self._match_tag(
                    TaxonomyType.packaging_shape.name, token.value
                ),
            }
        }

    def PACKAGING_MATERIALS(self, token):
        return {
            "material": {
                "value": token.value,
                "value_tag": self._match_tag(
                    TaxonomyType.packaging_material.name, token.value
                ),
            }
        }

    def junk(self, items):
        return Discard

    def _match_tag(self, type_: str, value: str) -> Optional[str]:
        taxonomy_map = self.taxonomy_maps[type_]
        value_tags = taxonomy_map.get(value, [])
        if not value_tags:
            raise ValueError("value %s not found in taxonomy %s", value, type)
        # Return first match
        return value_tags[0]


@functools.cache
def load_taxonomy_map(lang: str) -> dict[str, dict[str, list[str]]]:
    return {
        TaxonomyType.packaging_shape.name: load_json(  # type: ignore
            settings.GRAMMARS_DIR / f"terminal_packaging_shape_{lang}_map.json"
        ),
        TaxonomyType.packaging_material.name: load_json(  # type: ignore
            settings.GRAMMARS_DIR / f"terminal_packaging_material_{lang}_map.json"
        ),
        TaxonomyType.packaging_recycling.name: load_json(  # type: ignore
            settings.GRAMMARS_DIR / f"terminal_packaging_recycling_{lang}_map.json"
        ),
    }


def match_packaging(text: str) -> list[dict]:
    """Find packaging elements in the text using Lark parser.

    :param text: the input text
    :return: a list of detected packaging with up to 3 fields: `shape`,
      `material` and `recycling`. Each field has a `value` and a `value_tag`
      field. `value_tag` is None if the detected string could not be mapped
      to the taxonomy value or if the string maps to more than one taxonomy
      value (this shouldn't happen).
    """
    # Only fr is supported currently
    lang = "fr"
    grammar = load_grammar(lang)
    processed_text = normalize_string(text, lowercase=True, strip_accent=True)
    processed_text = strip_consecutive_spaces(processed_text)

    if not processed_text:
        # don't parse if text is empty after preprocessing
        return []

    t = grammar.parse(processed_text)
    return PackagingFRTransformer(load_taxonomy_map(lang)).transform(t)


def find_packaging(content: Union[OCRResult, str]) -> list[Prediction]:
    text = get_text(content)
    lang = "fr"
    if match := match_packaging(text):
        predictions = []
        for item in match:
            if "shape" not in item:
                # No shape defined
                # Safeguard, should not occur with current lark grammar
                logger.warning("No shape defined for packaging prediction %s", item)
                continue
            if item["shape"]["value_tag"] in SHAPE_ONLY_EXCLUDE_SET and not (
                item.get("material") or item.get("recycling")
            ):
                continue
            # We need to store some identifiable data in `value` field,
            # otherwise predictions from the same image won't be kept in DB
            value_hash_str = str(
                {
                    prop.value: item.get(prop.value, {}).get("value_tag")  # type: ignore
                    for prop in PackagingElementProperty
                }
            )
            prediction = Prediction(
                type=PredictionType.packaging,
                value_tag=None,
                value=value_hash_str,
                data={"lang": lang, "element": item},
                automatic_processing=False,
                predictor="grammar",
            )
            predictions.append(prediction)
        return predictions

    return []
