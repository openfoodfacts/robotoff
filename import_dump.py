import argparse
import json
import uuid

from robotoff.app.models import CategorizationTask


def iter_jsonl(jsonl_path):
    with open(str(jsonl_path), 'r') as f:
        for line in f:
            yield json.loads(line)


def import_text_dataset(filepath):
    data = []

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip('\n')

            if line:
                data.append(line)

    return data


def import_dump(jsonl_path, campaign=None, exclude_ids=None):
    inserts = []

    exclude_ids = exclude_ids or set()

    rows = 0
    for item in iter_jsonl(jsonl_path):
        product_id = item['code']

        if product_id in exclude_ids:
            continue

        insert = {
            'id': str(uuid.uuid4()),
            'product_id': product_id,
            'predicted_category': item['predicted_category_tag'],
            'confidence': item.get('predicted_category_prob'),
            'last_updated_at': str(item['last_modified_t']),
        }

        if 'category_depth' in item:
            insert['category_depth'] = item['category_depth']

        if campaign is not None:
            insert['campaign'] = campaign

        inserts.append(insert)
        rows += 1

        if rows % 100 == 0:
            CategorizationTask.insert_many(inserts).execute()
            inserts = []

    if inserts:
        CategorizationTask.insert_many(inserts).execute()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="path of dump JSONL file")
    parser.add_argument("--campaign", help="name of the campaign")
    parser.add_argument("--exclude-ids", help="filepath of IDs to exclude")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    exclude_ids = None

    if args.exclude_ids:
        exclude_ids = set(import_text_dataset(args.exclude_ids))

    import_dump(args.input, args.campaign, exclude_ids)
