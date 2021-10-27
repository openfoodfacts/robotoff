from typing import Dict, Iterable, List, Optional, Union

import peewee

from robotoff import settings
from robotoff.insights.annotate import (
    ALREADY_ANNOTATED_RESULT,
    UNKNOWN_INSIGHT_RESULT,
    SAVED_ANNOTATION_VOTE_RESULT,
    AnnotationResult,
    InsightAnnotatorFactory,
)
from robotoff.models import AnnotationVote, ProductInsight
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
    avoid_voted_by_username: Optional[str] = None,
    avoid_voted_by_device_id: Optional[str] = None,
    prioritize_voted: Optional[bool] = False,
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

    def join_with_no_votes_by(query, criteria):
        return query.join(
            AnnotationVote,
            join_type=peewee.JOIN.LEFT_OUTER,
            on=((AnnotationVote.insight_id == ProductInsight.id) & (criteria)),
        ).where(AnnotationVote.id.is_null())

    if avoid_voted_by_username:
        query = join_with_no_votes_by(
            query, (AnnotationVote.username == avoid_voted_by_username)
        )

    if avoid_voted_by_device_id:
        query = join_with_no_votes_by(
            query, (AnnotationVote.device_id == avoid_voted_by_device_id)
        )

    if where_clauses:
        query = query.where(*where_clauses)

    if count:
        return query.count()

    if limit is not None:
        query = query.limit(limit).offset(offset)

    if order_by is not None:
        if order_by == "random":
            query = query.order_by((peewee.fn.Random() * ProductInsight.n_votes).desc())

        elif order_by == "popularity":
            query = query.order_by(ProductInsight.unique_scans_n.desc())

        elif order_by == "n_votes":
            query = query.order_by(ProductInsight.n_votes.desc())

    if as_dict:
        query = query.dicts()

    return query.iterator()


def save_annotation(
    insight_id: str,
    annotation: int,
    device_id: str,
    update: bool = True,
    data: Optional[Dict] = None,
    auth: Optional[OFFAuthentication] = None,
    verify_annotation: bool = False,
) -> AnnotationResult:
"""Saves annotation either by using a single response as ground truth or by using several responses.

verify_annotation: controls whether we accept a single response(verify_annotation=False) as truth or whether we require several responses(=True) for annotation validation.
"""
    try:
        insight: Union[ProductInsight, None] = ProductInsight.get_by_id(insight_id)
    except ProductInsight.DoesNotExist:
        insight = None

    if not insight:
        return UNKNOWN_INSIGHT_RESULT

    if insight.annotation is not None:
        return ALREADY_ANNOTATED_RESULT

    if verify_annotation:
        verified: bool = False

        AnnotationVote.create(
            insight_id=insight_id,
            username=auth.get_username() if auth else None,
            value=annotation,
            device_id=device_id,
        )

        existing_votes = list(
            AnnotationVote.select(
                AnnotationVote.value,
                peewee.fn.COUNT(AnnotationVote.value).alias("num_votes"),
            )
            .where(AnnotationVote.insight_id == insight_id)
            .group_by(AnnotationVote.value)
            .order_by(peewee.SQL("num_votes").desc())
        )

        # Since we just atomically inserted the vote, we must have at least one row.
        if existing_votes[0].num_votes > 2:
            annotation = existing_votes[0].value
            if len(existing_votes) > 1 and existing_votes[1].num_votes >= 2:
                # This code credits the last person to contribute a vote with a potentially not their annotation.
                annotation = 0
            verified = True

        if not verified:
            return SAVED_ANNOTATION_VOTE_RESULT

    annotator = InsightAnnotatorFactory.get(insight.type)
    return annotator.annotate(insight, annotation, update, data=data, auth=auth)
