import datetime
import functools
from enum import Enum
from typing import Iterable, Literal, NamedTuple, Optional, Union

import peewee
from peewee import JOIN, SQL, fn

from robotoff import settings
from robotoff.app import events
from robotoff.insights.annotate import (
    ALREADY_ANNOTATED_RESULT,
    SAVED_ANNOTATION_VOTE_RESULT,
    UNKNOWN_INSIGHT_RESULT,
    AnnotationResult,
    annotate,
)
from robotoff.models import (
    AnnotationVote,
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    Prediction,
    ProductInsight,
    db,
)
from robotoff.off import OFFAuthentication
from robotoff.taxonomy import match_taxonomized_value
from robotoff.utils import get_logger
from robotoff.utils.text import get_tag

logger = get_logger(__name__)


class SkipVotedType(Enum):
    DEVICE_ID = 1
    USERNAME = 2


class SkipVotedOn(NamedTuple):
    """A helper class to specify whether a voted-on insight should be dropped from
    the get_insights results."""

    by: SkipVotedType
    id: str


def _add_vote_exclusions(
    query: peewee.Query, exclusion: Optional[SkipVotedOn]
) -> peewee.Query:
    if not exclusion:
        return query

    if exclusion.by == SkipVotedType.DEVICE_ID:
        criteria = AnnotationVote.device_id == exclusion.id
    elif exclusion.by == SkipVotedType.USERNAME:
        criteria = AnnotationVote.username == exclusion.id
    else:
        raise ValueError(f"Unknown SkipVoteType: {exclusion.by}")

    return query.join(
        AnnotationVote,
        join_type=peewee.JOIN.LEFT_OUTER,
        on=((AnnotationVote.insight_id == ProductInsight.id) & (criteria)),
    ).where(AnnotationVote.id.is_null())


def get_insights(
    barcode: Optional[str] = None,
    keep_types: Optional[list[str]] = None,
    country: Optional[str] = None,
    brands: Optional[list[str]] = None,
    annotated: Optional[bool] = False,
    annotation: Optional[int] = None,
    order_by: Optional[Literal["random", "popularity", "n_votes", "confidence"]] = None,
    value_tag: Optional[str] = None,
    server_domain: Optional[str] = None,
    reserved_barcode: Optional[bool] = None,
    as_dict: bool = False,
    limit: Optional[int] = 25,
    offset: Optional[int] = None,
    count: bool = False,
    avoid_voted_on: Optional[SkipVotedOn] = None,
    group_by_value_tag: Optional[bool] = False,
    automatically_processable: Optional[bool] = None,
    campaigns: Optional[list[str]] = None,
    predictor: Optional[str] = None,
) -> Iterable[ProductInsight]:
    """Fetch insights that meet the criteria passed as parameters.

    If the parameter value is None, no where clause will be added for this
    parameter.

    :param barcode: only keep insights with this barcode, defaults to None
    :param keep_types: only keep insights that have any of the these types,
        defaults to None
    :param country: only keep insights with this country, defaults to None
    :param brands: only keep insights that have any of these brands, defaults
        to None
    :param annotated: only keep annotated (True), not annotated (False
        insights), defaults to False
    :param annotation: only keep insights with a specific annotation value,
        defaults to None
    :param order_by: order results either randomly (random), by popularity
        (popularity), by number of votes on this insight (n_votes), by
        decreasing confidence score (confidence) or don't order results
        (None), defaults to None
    :param value_tag: only keep insights with this value_tag, defaults to None
    :param server_domain: Only keep insights with this server domain, defaults
        to `BaseUrlProvider.server_domain()`
    :param reserved_barcode: only keep insights with reserved barcodes (True)
        or without reserved barcode (False), defaults to None
    :param as_dict: if True, return results as dict instead of ProductInsight
        peewee objects, defaults to False
    :param limit: limit on the number of returned results, defaults to 25
    :param offset: query offset (used for pagination), defaults to None
    :param count: if True, return the number of results instead of the
        results, defaults to False
    :param avoid_voted_on: a SkipVotedOn used to remove results insights the
        user previously ignored, defaults to None
    :param group_by_value_tag: if True, group results by value_tag, defaults
        to False
    :param automatically_processable: only keep insights that are
        automatically processable (True) or not (False), defaults to None
    :param campaigns: only keep insights that have *all* of these campaigns,
        defaults to None
    :param predictor: only keep insights that have this predictor, defaults
        to None
    :return: the return value is either:
        - an iterable of ProductInsight objects or dict (if `as_dict=True`)
        - the number of products (if `count=True`)
        - a iterable of objects or dict (if `as_dict=True`) containing product
          count for each `value_tag`, if `group_by_value_tag=True`
    """
    if server_domain is None:
        server_domain = settings.BaseURLProvider.server_domain()

    where_clauses = [ProductInsight.server_domain == server_domain]

    if annotated is not None:
        where_clauses.append(ProductInsight.annotation.is_null(not annotated))

    if annotation is not None:
        where_clauses.append(ProductInsight.annotation == annotation)

    if automatically_processable is not None:
        where_clauses.append(
            ProductInsight.automatic_processing == automatically_processable
        )

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

    if campaigns is not None:
        where_clauses.append(ProductInsight.campaign.contains_all(campaigns))

    if predictor is not None:
        where_clauses.append(ProductInsight.predictor == predictor)

    query = _add_vote_exclusions(ProductInsight.select(), avoid_voted_on)

    if where_clauses:
        query = query.where(*where_clauses)

    if count:
        return query.count()

    if limit is not None:
        query = query.limit(limit)

    if offset is not None and order_by != "random":
        query = query.offset(offset)

    if group_by_value_tag:
        query = query.group_by(ProductInsight.value_tag).order_by(
            fn.COUNT(ProductInsight.id).desc()
        )
        query = query.select(
            ProductInsight.value_tag, fn.Count(ProductInsight.id)
        ).tuples()

    if order_by is not None:
        if order_by == "random":
            # The +1 is here to avoid 0*rand() = 0
            query = query.order_by(
                (peewee.fn.Random() * (ProductInsight.n_votes + 1)).desc()
            )

        elif order_by == "popularity":
            query = query.order_by(ProductInsight.unique_scans_n.desc())

        elif order_by == "confidence":
            query = query.order_by(SQL("confidence DESC NULLS LAST"))

        elif order_by == "n_votes":
            query = query.order_by(ProductInsight.n_votes.desc())

    if as_dict:
        query = query.dicts()

    return query.iterator()


def get_images(
    with_predictions: Optional[bool] = False,
    barcode: Optional[str] = None,
    server_domain: Optional[str] = None,
    offset: Optional[int] = None,
    count: bool = False,
    limit: Optional[int] = 25,
) -> Iterable[ImageModel]:
    if server_domain is None:
        server_domain = settings.BaseURLProvider.server_domain()

    where_clauses = [ImageModel.server_domain == server_domain]

    if barcode:
        where_clauses.append(ImageModel.barcode == barcode)

    query = ImageModel.select()

    if not with_predictions:
        # return only images without prediction
        query = query.join(ImagePrediction, JOIN.LEFT_OUTER).where(
            ImagePrediction.image.is_null()
        )

    if where_clauses:
        query = query.where(*where_clauses)

    if count:
        return query.count()
    else:
        return query.iterator()


def get_predictions(
    barcode: Optional[str] = None,
    keep_types: Optional[list[str]] = None,
    value_tag: Optional[str] = None,
    server_domain: Optional[str] = None,
    limit: Optional[int] = 25,
    offset: Optional[int] = None,
    count: bool = False,
) -> Iterable[Prediction]:
    if server_domain is None:
        server_domain = settings.BaseURLProvider.server_domain()

    where_clauses = [Prediction.server_domain == server_domain]

    if barcode:
        where_clauses.append(Prediction.barcode == barcode)

    if value_tag:
        where_clauses.append(Prediction.value_tag == value_tag)

    if keep_types:
        where_clauses.append(Prediction.type.in_(keep_types))

    query = Prediction.select()

    if where_clauses:
        query = query.where(*where_clauses)

    query = query.order_by(Prediction.id.desc())

    if count:
        return query.count()
    else:
        return query.iterator()


def get_image_predictions(
    with_logo: Optional[bool] = False,
    barcode: Optional[str] = None,
    type: Optional[str] = None,
    server_domain: Optional[str] = None,
    offset: Optional[int] = None,
    count: bool = False,
    limit: Optional[int] = 25,
) -> Iterable[ImagePrediction]:

    query = ImagePrediction.select()

    if server_domain is None:
        server_domain = settings.BaseURLProvider.server_domain()

    query = query.switch(ImagePrediction).join(ImageModel)
    where_clauses = [ImagePrediction.image.server_domain == server_domain]

    if barcode:
        where_clauses.append(ImagePrediction.image.barcode == barcode)

    if type:
        where_clauses.append(ImagePrediction.type == type)

    if not with_logo:
        # return only images without logo
        query = (
            query.switch(
                ImagePrediction
            )  # we need this because we may have joined with ImageModel
            .join(LogoAnnotation, JOIN.LEFT_OUTER)
            .where(LogoAnnotation.image_prediction.is_null())
        )

    if where_clauses:
        query = query.where(*where_clauses)

    query = query.order_by(LogoAnnotation.image_prediction.id.desc())

    if count:
        return query.count()
    else:
        return query.iterator()


def save_annotation(
    insight_id: str,
    annotation: int,
    device_id: str,
    update: bool = True,
    data: Optional[dict] = None,
    auth: Optional[OFFAuthentication] = None,
    trusted_annotator: bool = False,
) -> AnnotationResult:
    """Saves annotation either by using a single response as ground truth or
    by using several responses.

    If annotation == -1 (ignore), we consider the annotation as a vote, so
    that we don't return the insight to the user again.
    If there are >= 2 votes on one of the 2 other possible values (0/1),
    including the vote in process, we set the annotation value of the largest
    voting group. The only exception is when both groups >= 2 votes, in which
    case we mark the insight as invalid (annotation=-1).
    Note that `annotation=-1` has two different meanings here: if it's a vote,
    we consider it as a "ignore", and if it's the insight annotation value we
    consider the insight as invalid, so that it's not available for annotation
    again.

    :param insight_id: The ID of the insight
    :param annotation: The annotation, either -1, 0, or 1
    :param device_id: Unique identifier of the device, see
      `device_id_from_request`
    :param update: If True, perform the update on Product Opener if annotation=1,
      otherwise only save the annotation (default: True)
    :param data: Optional additional data, required for some insight types
    :param auth: User authentication data
    :param trusted_annotator: Defines whether the given annotation comes from
    an authoritative source (e.g. a trusted user), ot whether the annotation
    should be subject to the voting system.
    """
    try:
        insight: Union[ProductInsight, None] = ProductInsight.get_by_id(insight_id)
    except ProductInsight.DoesNotExist:
        insight = None

    if not insight:
        return UNKNOWN_INSIGHT_RESULT

    if insight.annotation is not None:
        return ALREADY_ANNOTATED_RESULT

    # We use AnnotationVote mechanism to save annotation = -1 (ignore) for
    # authenticated users, so that it's not returned again to the user
    if not trusted_annotator or annotation == -1:
        verified = False

        AnnotationVote.create(
            insight_id=insight_id,
            username=auth.get_username() if auth else None,
            value=annotation,
            device_id=device_id,
        )

        with db.atomic() as tx:
            try:
                existing_votes = list(
                    AnnotationVote.select(
                        AnnotationVote.value,
                        peewee.fn.COUNT(AnnotationVote.value).alias("num_votes"),
                    )
                    .where(
                        AnnotationVote.insight_id == insight_id,
                        # We don't consider any ignore (annotation = -1) vote
                        AnnotationVote.value != -1,
                    )
                    .group_by(AnnotationVote.value)
                    .order_by(peewee.SQL("num_votes").desc())
                )
                insight.n_votes = functools.reduce(
                    lambda sum, row: sum + row.num_votes, existing_votes, 0
                )
                insight.save()
            except Exception as e:
                tx.rollback()
                raise e

        if existing_votes:
            # If the top annotation has 3 or more votes, consider applying it to the insight.
            if existing_votes[0].num_votes >= 3:
                annotation = existing_votes[0].value
                verified = True

            # But first check for the following cases:
            #  1) The 1st place annotation has > 2 votes, and the 2nd place annotation has >= 2 votes.
            #  2) 1st place and 2nd place have 2 votes each.
            #
            # In both cases, we consider this an ambiguous result and mark it with 'I don't know'.
            if (
                existing_votes[0].num_votes >= 2
                and len(existing_votes) > 1
                and existing_votes[1].num_votes >= 2
            ):
                # This code credits the last person to contribute a vote with a potentially not their annotation.
                annotation = -1
                verified = True

        if not verified:
            return SAVED_ANNOTATION_VOTE_RESULT

    result = annotate(insight, annotation, update, data=data, auth=auth)
    username = auth.get_username() if auth else "unknown annotator"
    events.event_processor.send_async(
        "question_answered", username, device_id, insight.barcode
    )
    return result


def get_logo_annotation(
    barcode: Optional[str] = None,
    keep_types: Optional[list[str]] = None,
    value_tag: Optional[str] = None,
    server_domain: Optional[str] = None,
    limit: Optional[int] = 25,
    offset: Optional[int] = None,
    count: bool = False,
) -> Iterable[LogoAnnotation]:

    if server_domain is None:
        server_domain = settings.BaseURLProvider.server_domain()

    query = LogoAnnotation.select().join(ImagePrediction).join(ImageModel)

    where_clauses = [
        LogoAnnotation.image_prediction.image.server_domain == server_domain
    ]

    if barcode:
        where_clauses.append(LogoAnnotation.barcode == barcode)

    if value_tag:
        where_clauses.append(LogoAnnotation.annotation_value_tag == value_tag)

    if keep_types:
        where_clauses.append(LogoAnnotation.annotation_type.in_(keep_types))

    if where_clauses:
        query = query.where(*where_clauses)

    if limit is not None:
        query = query.limit(limit)

    if offset is not None:
        query = query.offset(offset)

    query = query.order_by(LogoAnnotation.image_prediction.id.desc())

    if count:
        return query.count()
    else:
        return query.iterator()


def update_logo_annotations(
    annotation_logos: list[tuple[str, Optional[str], LogoAnnotation]],
    username: str,
    completed_at: datetime.datetime,
) -> list[LogoAnnotation]:
    updated_fields = set()
    updated_logos = []
    for type_, value, logo in annotation_logos:
        logo.annotation_type = type_
        updated_fields.add("annotation_type")

        if value is not None:
            value_tag = get_tag(value)
            logo.annotation_value = value
            logo.annotation_value_tag = value_tag
            logo.taxonomy_value = match_taxonomized_value(value_tag, type_)
            logo.username = username
            logo.completed_at = completed_at
            updated_fields |= {
                "annotation_value",
                "annotation_value_tag",
                "taxonomy_value",
                "username",
                "completed_at",
            }
        updated_logos.append(logo)

    if updated_logos:
        LogoAnnotation.bulk_update(updated_logos, fields=list(updated_fields))

    return updated_logos
