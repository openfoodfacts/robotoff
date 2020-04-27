import pathlib
from random import shuffle

from robotoff import settings
from robotoff.utils import jsonl_iter, dump_jsonl


lang = "pt"
input_path: pathlib.Path = settings.DATASET_DIR / "category" / "category_{}.jsonl".format(
    lang
)

items = list(jsonl_iter(input_path))
shuffle(items)

val_count = len(items) // 10
val_items = items[:val_count]
test_items = items[val_count : 2 * val_count]
train_items = items[2 * val_count :]


dump_jsonl(input_path.with_name("category_{}.val.jsonl".format(lang)), val_items)
dump_jsonl(input_path.with_name("category_{}.test.jsonl".format(lang)), test_items)
dump_jsonl(input_path.with_name("category_{}.train.jsonl".format(lang)), train_items)
