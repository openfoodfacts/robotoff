import csv

from robotoff.taxonomy import get_taxonomy

for taxonomy_name in ("ingredient", "category", "label"):
    taxonomy = get_taxonomy(taxonomy_name)

    with open(f"{taxonomy_name}.tsv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "description"])
        writer.writeheader()

        for node in taxonomy.iter_nodes():
            name = node.get_localized_name("en")

            if name != node.id:
                writer.writerow({"id": node.id, "name": name, "description": name})
