import functools
from enum import Enum
from typing import Iterable, NamedTuple, Optional, Union

import peewee
from peewee import JOIN, fn

from robotoff import settings
from robotoff.app import events
from robotoff.insights.annotate import (
    ALREADY_ANNOTATED_RESULT,
    SAVED_ANNOTATION_VOTE_RESULT,
    UNKNOWN_INSIGHT_RESULT,
    AnnotationResult,
    InsightAnnotatorFactory,
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
from robotoff.utils import get_logger

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
    order_by: Optional[str] = None,
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
    campaign: Optional[str] = None,
    predictor: Optional[str] = None,
) -> Iterable[ProductInsight]:
    if server_domain is None:
        server_domain = settings.OFF_SERVER_DOMAIN

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

    if campaign is not None:
        where_clauses.append(ProductInsight.campaign.contains(campaign))

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
        server_domain = settings.OFF_SERVER_DOMAIN

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
        server_domain = settings.OFF_SERVER_DOMAIN

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
        server_domain = settings.OFF_SERVER_DOMAIN

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

    annotator = InsightAnnotatorFactory.get(insight.type)
    result = annotator.annotate(insight, annotation, update, data=data, auth=auth)
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
        server_domain = settings.OFF_SERVER_DOMAIN

    query = LogoAnnotation.select().join(ImagePrediction).join(ImageModel)

    where_clauses = [
        LogoAnnotation.image_prediction.image.server_domain == server_domain
    ]

    if barcode:
        where_clauses.append(LogoAnnotation.image_prediction.image.barcode == barcode)

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
