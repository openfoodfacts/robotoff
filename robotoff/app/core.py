from typing import Union, Optional, List, Iterable

from robotoff.insights.annotate import (InsightAnnotatorFactory,
                                        AnnotationResult,
                                        ALREADY_ANNOTATED_RESULT,
                                        UNKNOWN_INSIGHT_RESULT)
from robotoff.models import ProductInsight
from robotoff.utils import get_logger

import peewee


logger = get_logger(__name__)


def get_insights(barcode: Optional[str] = None,
                 keep_types: List[str] = None,
                 country: str = None,
                 brands: List[str] = None,
                 annotated: Optional[bool] = False,
                 random_order: bool = False,
                 value_tag: Optional[str] = None,
                 count: Optional[int] = 25) -> Iterable[ProductInsight]:
    where_clauses = []

    if annotated is not None:
        where_clauses.append(ProductInsight.annotation.is_null(not annotated))

    if barcode:
        where_clauses.append(ProductInsight.barcode == barcode)

    if value_tag:
        where_clauses.append(ProductInsight.value_tag == value_tag)

    if keep_types:
        where_clauses.append(ProductInsight.type.in_(keep_types))

    if country is not None:
        where_clauses.append(ProductInsight.countries.contains(
            country))

    if brands:
        where_clauses.append(ProductInsight.brands.contains_any(
            brands))

    query = ProductInsight.select()

    if where_clauses:
        query = query.where(*where_clauses)

    if count is not None:
        query = query.limit(count)

    if random_order:
        query = query.order_by(peewee.fn.Random())

    return query.iterator()


def save_insight(insight_id: str,
                 annotation: int,
                 update: bool = True,
                 session_cookie: Optional[str] = None) \
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
    return annotator.annotate(insight, annotation, update,
                              session_cookie=session_cookie)
