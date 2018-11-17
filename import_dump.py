import datetime
import json
import uuid

from models import CategorizationTask


def iter_jsonl(jsonl_path):
    with open(str(jsonl_path), 'r') as f:
        for line in f:
            yield json.loads(line)


def import_dump(jsonl_path):
    inserts = []

    for item in iter_jsonl(jsonl_path):
        insert = {
            'id': str(uuid.uuid4()),
            'product_id': item['code'],
            'predicted_category': item['predicted_categories_tag'],
            'confidence': item['predicted_categories_prob'],
            'last_updated_at': item['last_modified_t'],
        }
        inserts.append(insert)

    CategorizationTask.insert_many(inserts).execute()


if __name__ == "__main__":
    import_dump("/home/raphael/Projets/openfoodfacts-ui/predicted_categories.json")
