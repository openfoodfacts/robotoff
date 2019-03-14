from typing import Union, Optional, List, Iterable

from robotoff.insights.annotate import (InsightAnnotatorFactory,
                                        AnnotationResult,
                                        ALREADY_ANNOTATED_RESULT,
                                        UNKNOWN_INSIGHT_RESULT)
from robotoff.models import ProductInsight
from robotoff.off import get_product
from robotoff.slack import notify_manual_processing
from robotoff.utils import get_logger

import peewee


logger = get_logger(__name__)


CATEGORY_PRODUCT_FIELDS = [
    'image_front_url',
    'product_name',
    'brands',
    'categories_tags',
    'code',
]


def normalize_lang(lang):
    if lang is None:
        return

    if '-' in lang:
        return lang.split('-')[0]

    return lang


def parse_product_json(data, lang=None):
    product = {
        'image_url': data.get('image_front_url'),
        'product_name': data.get('product_name'),
        'brands': data.get('brands'),
        'categories_tags': list(set(data.get('categories_tags', []))),
    }

    if lang is None:
        domain = "https://world.openfoodfacts.org"
    else:
        domain = "https://{}.openfoodfacts.org".format(lang)

    product['product_link'] = "{}/product/{}".format(domain, data.get('code'))
    product['edit_product_link'] = "{}/cgi/product.pl?type=edit&code={}".format(domain, data.get('code'))

    return product


def get_insights(barcode: str,
                 keep_types: List[str] = None,
                 count=25) -> Iterable[ProductInsight]:
    where_clauses = [
        ProductInsight.annotation.is_null(),
        ProductInsight.barcode == barcode
    ]

    if keep_types:
        where_clauses.append(ProductInsight.type.in_(keep_types))

    query = (ProductInsight.select()
                           .where(*where_clauses)
                           .limit(count))
    return query.iterator()


def get_random_insight(insight_type: str = None,
                       country: str = None) -> Optional[ProductInsight]:
    attempts = 0
    while True:
        attempts += 1

        if attempts > 4:
            return None

        query = ProductInsight.select()
        where_clauses = [ProductInsight.annotation.is_null()]

        if country is not None:
            where_clauses.append(ProductInsight.countries.contains(
                country))

        if insight_type is not None:
            where_clauses.append(ProductInsight.type ==
                                 insight_type)

        query = query.where(*where_clauses).order_by(peewee.fn.Random())

        insight_list = list(query.limit(1))

        if not insight_list:
            return None

        insight = insight_list[0]
        # We only need to know if the product exists, so fetching barcode
        # is enough
        product = get_product(insight.barcode, ['code'])

        # Product may be None if not found
        if product:
            return insight
        else:
            insight.delete_instance()
            logger.info("Product not found, insight deleted")


def save_insight(insight_id: str, annotation: int, update: bool=True) -> AnnotationResult:
    try:
        insight: Union[ProductInsight, None] \
            = ProductInsight.get_by_id(insight_id)
    except ProductInsight.DoesNotExist:
        insight = None

    if not insight:
        return UNKNOWN_INSIGHT_RESULT

    if insight.annotation is not None:
        return ALREADY_ANNOTATED_RESULT

    if update:
        notify_manual_processing(insight, annotation)

    annotator = InsightAnnotatorFactory.get(insight.type)
    return annotator.annotate(insight, annotation, update)
