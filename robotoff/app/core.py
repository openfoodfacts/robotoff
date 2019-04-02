import tempfile

import requests
from typing import Union, Optional, List, Iterable

from robotoff.insights.annotate import (InsightAnnotatorFactory,
                                        AnnotationResult,
                                        ALREADY_ANNOTATED_RESULT,
                                        UNKNOWN_INSIGHT_RESULT)
from robotoff.models import ProductInsight
from robotoff.off import get_product
from robotoff.utils import get_logger
from PIL import Image

import peewee


logger = get_logger(__name__)


def get_insights(barcode: Optional[str] = None,
                 keep_types: List[str] = None,
                 country: str = None,
                 brands: List[str] = None,
                 count=25) -> Iterable[ProductInsight]:
    where_clauses = [
        ProductInsight.annotation.is_null(),
    ]

    if barcode:
        where_clauses.append(ProductInsight.barcode == barcode)

    if keep_types:
        where_clauses.append(ProductInsight.type.in_(keep_types))

    if country is not None:
        where_clauses.append(ProductInsight.countries.contains(
            country))

    if brands:
        where_clauses.append(ProductInsight.brands.contains_any(
            brands))

    query = (ProductInsight.select()
                           .where(*where_clauses)
                           .limit(count)
                           .order_by(peewee.fn.Random()))
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


def save_insight(insight_id: str, annotation: int, update: bool = True) \
        -> AnnotationResult:
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


def get_image_from_url(image_url: str) -> Optional[Image.Image]:
    r = requests.get(image_url)

    if r.status_code != 200:
        return None

    with tempfile.NamedTemporaryFile() as f:
        f.write(r.content)
        image = Image.open(f.name)

    return image
