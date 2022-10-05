import hashlib
from typing import Dict, Iterable, Tuple

from robotoff.insights import InsightType
from robotoff.taxonomy import Taxonomy, get_taxonomy
from robotoff.utils import get_logger

logger = get_logger()


SUPPORTED_LANG = {
    "fr",
    "en",
    "es",
    "de",
}


def generate_category_data() -> Iterable[Tuple[str, Dict]]:
    category_taxonomy: Taxonomy = get_taxonomy(InsightType.category.name)

    for category_node in category_taxonomy.iter_nodes():
        supported_langs = [
            lang for lang in category_node.names if lang in SUPPORTED_LANG
        ]

        data = {
            "{}:name".format(lang): category_node.names[lang]
            for lang in supported_langs
        }
        data["id"] = category_node.id

        id_ = hashlib.sha256(category_node.id.encode("utf-8")).hexdigest()

        yield id_, data
