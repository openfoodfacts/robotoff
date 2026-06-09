import pathlib
from random import shuffle

from robotoff import settings
from robotoff.utils import dump_jsonl, jsonl_iter

lang = "pt"
input_path: pathlib.Path = settings.DATASET_DIR / "category" / f"category_{lang}.jsonl"

items = list(jsonl_iter(input_path))
shuffle(items)

val_count = len(items) // 10
val_items = items[:val_count]
test_items = items[val_count : 2 * val_count]
train_items = items[2 * val_count :]


dump_jsonl(input_path.with_name(f"category_{lang}.val.jsonl"), val_items)
dump_jsonl(input_path.with_name(f"category_{lang}.test.jsonl"), test_items)
dump_jsonl(input_path.with_name(f"category_{lang}.train.jsonl"), train_items)
