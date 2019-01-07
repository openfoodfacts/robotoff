import argparse
import json
import uuid

from robotoff.app.models import CategorizationTask


def iter_jsonl(jsonl_path):
    with open(str(jsonl_path), 'r') as f:
        for line in f:
            yield json.loads(line)


def import_dump(jsonl_path, campaign=None):
    inserts = []
    print("Deleting old predictions")
    CategorizationTask.delete().where(CategorizationTask.annotation.is_null()).execute()

    print("Fetching already labeled product IDs")
    exclude_ids = set(CategorizationTask.select(CategorizationTask.product_id)
                      .where(CategorizationTask.annotation.is_null(False)).scalar())
    print("Inserting new prediction in DB")

    rows = 0
    excluded = 0

    for item in iter_jsonl(jsonl_path):
        product_id = item['code']

        if product_id in exclude_ids:
            excluded += 1
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

        if 'countries_tags' in item:
            insert['countries'] = item['countries_tags']

        inserts.append(insert)
        rows += 1

        if rows % 100 == 0:
            CategorizationTask.insert_many(inserts).execute()
            inserts = []

    if inserts:
        CategorizationTask.insert_many(inserts).execute()

    print("Insertion finished, %d items inserted, "
          "%d excluded" % (rows, excluded))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="path of dump JSONL file")
    parser.add_argument("--campaign", help="name of the campaign")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    import_dump(args.input, args.campaign)
