from typing import Dict, Iterable, List, Optional, Union

import peewee

from robotoff import settings
from robotoff.insights.annotate import (
    ALREADY_ANNOTATED_RESULT,
    UNKNOWN_INSIGHT_RESULT,
    AnnotationResult,
    InsightAnnotatorFactory,
)
from robotoff.models import ProductInsight
from robotoff.off import OFFAuthentication
from robotoff.utils import get_logger

logger = get_logger(__name__)


def get_insights(
    barcode: Optional[str] = None,
    keep_types: List[str] = None,
    country: str = None,
    brands: List[str] = None,
    annotated: Optional[bool] = False,
    annotation: Optional[int] = None,
    order_by: Optional[str] = None,
    value_tag: Optional[str] = None,
    server_domain: Optional[str] = None,
    reserved_barcode: Optional[bool] = None,
    as_dict: bool = False,
    limit: Optional[int] = 25,
    offset: Optional[int] = None,
    count: bool = False,
    latent: Optional[bool] = False,
) -> Iterable[ProductInsight]:
    if server_domain is None:
        server_domain = settings.OFF_SERVER_DOMAIN

    where_clauses = [ProductInsight.server_domain == server_domain]

    if latent is not None:
        where_clauses.append(ProductInsight.latent == latent)

    if annotated is not None:
        where_clauses.append(ProductInsight.annotation.is_null(not annotated))

    if annotation is not None:
        where_clauses.append(ProductInsight.annotation == annotation)

    if barcode:
        where_clauses.append(ProductInsight.barcode == barcode)

    if value_tag:
        where_clauses.append(ProductInsight.value_tag == value_tag)

    if keep_types:
        where_clauses.append(ProductInsight.type.in_(keep_types))

    if country is not None:
        where_clauses.append(ProductInsight.countries.contains(country))

    if brands:
        where_clauses.append(ProductInsight.brands.contains_any(brands))

    if reserved_barcode is not None:
        where_clauses.append(ProductInsight.reserved_barcode == reserved_barcode)

    query = ProductInsight.select()

    if where_clauses:
        query = query.where(*where_clauses)

    if count:
        return query.count()

    if limit is not None:
        query = query.limit(limit).offset(offset)

    if order_by is not None:
        if order_by == "random":
            query = query.order_by(peewee.fn.Random())

        elif order_by == "popularity":
            query = query.order_by(ProductInsight.unique_scans_n.desc())

    if as_dict:
        query = query.dicts()

    return query.iterator()


def save_insight(
    insight_id: str,
    annotation: int,
    update: bool = True,
    data: Optional[Dict] = None,
    auth: Optional[OFFAuthentication] = None,
) -> AnnotationResult:
    try:
        insight: Union[ProductInsight, None] = ProductInsight.get_by_id(insight_id)
    except ProductInsight.DoesNotExist:
        insight = None

    if not insight:
        return UNKNOWN_INSIGHT_RESULT

    if insight.annotation is not None:
        return ALREADY_ANNOTATED_RESULT

    annotator = InsightAnnotatorFactory.get(insight.type)
    return annotator.annotate(insight, annotation, update, data=data, auth=auth)
