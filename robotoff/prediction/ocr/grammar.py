from pathlib import Path
from typing import Optional

from robotoff.taxonomy import Taxonomy, TaxonomyType, get_taxonomy
from robotoff.utils import dump_json, get_logger
from robotoff.utils.text import strip_accents_v2

logger = get_logger(__name__)


def normalize_string(text: str, lowercase: bool, strip_accent: bool) -> str:
    """Normalize names/synonyms of taxonomy nodes or input text before
    performing grammar parsing."""
    if lowercase:
        text = text.lower()
    if strip_accent:
        text = strip_accents_v2(text)
    return text


def extract_taxonomy_names(
    lang: str,
    taxonomy: Taxonomy,
    ignore_ids: set[str],
    add_synonyms: bool,
    add_xx: bool,
    lowercase: bool,
    strip_accent: bool,
) -> list[tuple[str, str]]:
    """Extract normalized name/synonyms of all taxonomy nodes.

    This function returns a single list of
    (taxonomy node ID, normalized name string) tuples. Items are grouped by
    node ID.

    :param lang: language to use to extract nodes
    :param taxonomy: the Taxonomy to use
    :param ignore_ids: a set of node IDs to ignore
    :param add_synonyms: if True, also add synonyms, otherwise only the name
      is included
    :param add_xx: if True, add language-independent (xx) translation
    :param lowercase: if True, lowercase names/synonyms
    :param strip_accent: if True, remove accents from names/synonyms
    """
    output = []
    for node in taxonomy.iter_nodes():
        if lang not in node.names or node.id in ignore_ids:
            continue

        names = []
        if node.names[lang]:
            # Sometimes it's null
            names.append(node.names[lang])

        if add_xx and "xx" in node.names:
            names.append(node.names["xx"])

        if add_synonyms:
            names += node.synonyms.get(lang, [])
            if add_xx:
                names += node.synonyms.get("xx", [])

        names = [normalize_string(name, lowercase, strip_accent) for name in names]
        # Strip items and remove empty ones
        names = [name.strip() for name in names if name.strip()]
        # Remove duplicates, but keep original order
        output += [
            (node.id, name) for name in sorted(set(names), key=lambda x: names.index(x))
        ]

    return output


def generate_terminal_symbols_file(
    output_path: Path,
    lang: str,
    terminal_name: str,
    taxonomy_type: TaxonomyType,
    terminal_priority: Optional[int] = None,
    lowercase: bool = True,
    strip_accent: bool = True,
    add_synonyms: bool = True,
    add_xx: bool = True,
    ignore_ids: Optional[set[str]] = None,
    raises: bool = True,
):
    """Generate lark terminal symbol file from a taxonomy."""
    content, name_to_id_mapping = generate_terminal_symbols_text(
        lang=lang,
        terminal_name=terminal_name,
        taxonomy_type=taxonomy_type,
        terminal_priority=terminal_priority,
        lowercase=lowercase,
        strip_accent=strip_accent,
        add_synonyms=add_synonyms,
        add_xx=add_xx,
        ignore_ids=ignore_ids,
        raises=raises,
    )

    with output_path.open("w") as f:
        f.write("// This file has been generated automatically, DO NOT EDIT!\n")
        f.write(content)

    map_path = output_path.parent / f"{output_path.stem}_map.json"
    dump_json(map_path, name_to_id_mapping)


def generate_terminal_symbols_text(
    lang: str,
    terminal_name: str,
    taxonomy_type: TaxonomyType,
    terminal_priority: Optional[int] = None,
    lowercase: bool = True,
    strip_accent: bool = True,
    add_synonyms: bool = True,
    add_xx: bool = True,
    ignore_ids: Optional[set[str]] = None,
    raises: bool = True,
) -> tuple[str, dict[str, list[str]]]:
    """Generate the text of a lark terminal symbol file from a taxonomy.

    :param terminal_name: name of the terminal symbol in the lark file
    :param taxonomy_type: TaxonomyType of the taxonomy to use to generate
      lark terminal symbol text content
    :param terminal_priority: priority of the terminal, by default no priority
    is provided and lark set priority to 0 for the terminal (lowest)
    priority by default

    See `extract_taxonomy_names` for documentation about remaining parameters.
    """
    ignore_ids = ignore_ids or set()
    texts = []
    taxonomy = get_taxonomy(taxonomy_type.name, offline=True)
    seen_set: dict[str, str] = {}

    node_id_names = extract_taxonomy_names(
        lang, taxonomy, ignore_ids, add_synonyms, add_xx, lowercase, strip_accent
    )
    for node_id, name in node_id_names:
        if name in seen_set:
            # The normalized name matches more than one node in the taxonomy
            error_message = "item %s (node %s) already seen for node %s!"
            args = (name, node_id, seen_set[name])
            if raises:
                raise ValueError(error_message % args)
            else:
                logger.warning(error_message, *args)
        seen_set[name] = node_id

    first_node = True
    name_to_id_mapping: dict[str, list[str]] = {}
    # Sort node_id_names by decreasing name size, it's necessary for lark to
    # match longuest terminal correctly
    for node_id, name in sorted(node_id_names, key=lambda x: len(x[1]), reverse=True):
        name_to_id_mapping.setdefault(name, []).append(node_id)
        if first_node:
            # Add the first line of the terminal definition
            # "{NAME}.{PRIORITY}: " if priority is provided, otherwise "{NAME}: "
            terminal_priority_str = (
                terminal_priority if terminal_priority is not None else ""
            )
            item = f"{terminal_name}.{terminal_priority_str}: "
            first_node = False
            len_first_item = len(item) - 2
        else:
            # Align subsequent lines with first line for easier reading
            item = f"{' ' * len_first_item}| "

        # Escape '/' character
        name = name.replace("/", "\\/")
        # Add the name to the terminal list, adding \b before and after the
        # string so that it doesn't match words with extra characters
        item += f'/\\b{name}\\b/  // "{node_id}"'
        texts.append(item)

    texts.append("\n")
    return "\n".join(texts), name_to_id_mapping
