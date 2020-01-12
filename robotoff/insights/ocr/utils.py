from typing import Iterable, Optional, Callable

from flashtext import KeywordProcessor

from robotoff.utils.text import strip_accents_ascii


def generate_keyword_processor(items: Iterable[str],
                               keep_func: Optional[Callable] = None) -> KeywordProcessor:
    processor = KeywordProcessor()

    for item in items:
        key, name = item.split('||')

        if keep_func is not None and not keep_func(key, name):
            continue

        processor.add_keyword(name, clean_name=(key, name))

    return processor


def get_tag(brand: str) -> str:
    brand = strip_accents_ascii(brand)
    return (brand.lower()
                 .replace(' & ', '-')
                 .replace(' ', '-')
                 .replace("'", '-'))
