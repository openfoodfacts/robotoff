from typing import Union, Optional

from robotoff.insights.annotate import (InsightAnnotatorFactory,
                                        AnnotationResult,
                                        ALREADY_ANNOTATED_RESULT,
                                        UNKNOWN_INSIGHT_RESULT)
from robotoff.models import ProductInsight
from robotoff.categories import parse_category_json
from robotoff.off import get_product
from robotoff.utils import get_logger
from robotoff import settings

import peewee


category_json = parse_category_json(settings.CATEGORIES_PATH)

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


def get_category_name(identifier, lang):
    if identifier not in category_json:
        return identifier

    category = category_json[identifier]
    category_names = category['name']

    if lang in category_names:
        return category_names[lang]

    if 'en' in category_names:
        return category_names['en']

    return identifier


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


def get_insights(barcode: str, limit=25):
    query = (ProductInsight.select()
                           .where(ProductInsight.annotation
                                  .is_null(),
                                  ProductInsight.barcode ==
                                  barcode)
                           .limit(limit))

    insights = []

    for insight in query.iterator():
        insights.append(insight.serialize())

    return insights


def get_random_insight(insight_type: str = None,
                       country: str = None) -> Optional[ProductInsight]:
    attempts = 0
    while True:
        attempts += 1

        if attempts > 4:
            return

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
            return

        insight = insight_list[0]
        # We only need to know if the product exists, so fetching barcode
        # is enough
        product = get_product(insight.barcode, ['code'])

        # Product may be None if not found
        if product:
            return insight
        else:
            insight.outdated = True
            insight.save()
            logger.info("Product not found")


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

    annotator = InsightAnnotatorFactory.get(insight.type)
    return annotator.annotate(insight, annotation, update)
