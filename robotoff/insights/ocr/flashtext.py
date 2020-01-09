from typing import Iterable, Optional, Callable

from flashtext import KeywordProcessor


def generate_keyword_processor(items: Iterable[str],
                               keep_func: Optional[Callable] = None) -> KeywordProcessor:
    processor = KeywordProcessor()

    for item in items:
        key, name = item.split('||')

        if keep_func is not None and not keep_func(key, name):
            continue

        processor.add_keyword(name, clean_name=(key, name))

    return processor
