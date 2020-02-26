from typing import Iterable

from robotoff import settings
from robotoff.ml.category.neural.model import predict_from_product_batch
from robotoff.products import ProductDataset
from robotoff.utils import get_logger, dump_jsonl
from robotoff.utils.types import JSONType

logger = get_logger()

lang = 'it'


def updated_product_add_category_insight(products: Iterable[JSONType],
                                         batch_size: int):
    insights = predict_from_product_batch(products,
                                          allowed_lang={lang},
                                          filter_blacklisted=True,
                                          batch_size=batch_size)

    dump_jsonl(settings.PROJECT_DIR / 'category_insights.{}.jsonl'.format(lang),
               insights)


def main():
    dataset = ProductDataset.load()

    training_stream = (dataset.stream()
                       .filter_text_field('lang', lang)
                       .filter_nonempty_text_field('product_name_{}'.format(lang)))

    updated_product_add_category_insight(training_stream.iter(), batch_size=1024)


if __name__ == "__main__":
    main()
