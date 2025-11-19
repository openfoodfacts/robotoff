import datetime
import functools
import logging
from enum import Enum
from typing import Iterable, Literal, NamedTuple, Union

import falcon
import peewee
from openfoodfacts.types import COUNTRY_CODE_TO_NAME, Country
from peewee import JOIN, SQL, fn
from pydantic import BaseModel, ValidationError

from robotoff.app import events
from robotoff.insights.annotate import (
    ALREADY_ANNOTATED_RESULT,
    SAVED_ANNOTATION_VOTE_RESULT,
    UNKNOWN_INSIGHT_RESULT,
    AnnotationResult,
    annotate,
)
from robotoff.insights.question import QuestionFormatterFactory
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
from robotoff.types import InsightAnnotation, JSONType, ServerType
from robotoff.utils.text import get_tag

logger = logging.getLogger(__name__)


class SkipVotedType(Enum):
    DEVICE_ID = 1
    USERNAME = 2


class SkipVotedOn(NamedTuple):
    """A helper class to specify whether a voted-on insight should be dropped
    from the get_insights results."""

    by: SkipVotedType
    id: str


def _add_vote_exclusion_clause(exclusion: SkipVotedOn) -> peewee.Expression:
    """Return a peewee expression to exclude insights that have been voted on
    by the user."""
    if exclusion.by == SkipVotedType.DEVICE_ID:
        criteria = AnnotationVote.device_id == exclusion.id
    elif exclusion.by == SkipVotedType.USERNAME:
        criteria = AnnotationVote.username == exclusion.id
    else:
        raise ValueError(f"Unknown SkipVoteType: {exclusion.by}")

    return ProductInsight.id.not_in(
        AnnotationVote.select(AnnotationVote.insight_id).where(criteria)
    )


def get_insights(
    barcode: str | None = None,
    server_type: ServerType = ServerType.off,
    keep_types: list[str] | None = None,
    countries: list[Country] | None = None,
    brands: list[str] | None = None,
    annotated: bool | None = False,
    annotation: int | None = None,
    order_by: Literal["random", "popularity", "n_votes", "confidence"] | None = None,
    value_tag: str | None = None,
    reserved_barcode: bool | None = None,
    as_dict: bool = False,
    limit: int | None = 25,
    offset: int | None = None,
    count: bool = False,
    max_count: int | None = None,
    avoid_voted_on: SkipVotedOn | None = None,
    group_by_value_tag: bool | None = False,
    automatically_processable: bool | None = None,
    campaigns: list[str] | None = None,
    predictor: str | None = None,
    lc: list[str] | None = None,
    with_image: bool | None = None,
) -> Iterable[ProductInsight]:
    """Fetch insights that meet the criteria passed as parameters.

    If the parameter value is None, no where clause will be added for this
    parameter.

    :param barcode: only keep insights with this barcode, defaults to None
    :param server_type: the server type of the insights, defaults to
        ServerType.off
    :param keep_types: only keep insights that have any of the these types,
        defaults to None
    :param countries: only keep insights with `country` in this list of
        countries, defaults to None
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
    :param reserved_barcode: only keep insights with reserved barcodes (True)
        or without reserved barcode (False), defaults to None
    :param as_dict: if True, return results as dict instead of ProductInsight
        peewee objects, defaults to False
    :param limit: limit on the number of returned results, defaults to 25
    :param offset: query offset (used for pagination), defaults to None
    :param count: if True, return the number of results instead of the
        results, defaults to False
    :param count_max: an upper bound on the number of insights to count,
        defaults to None. If provided, the count will be limited to this
        value. It allows to dramatically speed up the count query.
        If not provided, an exact count will be returned.
    :param max_count: an upper bound on the number of insights to return when
        asking for the count (`count=True`), defaults to None (no limit).
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
    :param lc: only keep insights that have any `insight.lc` in this
        list of language codes, defaults to None
        It is used to filter lang of ingredient_spellcheck
    :param with_image: only keep insights that have an associated image (True)
        or not (False), defaults to None
    :return: the return value is either:
        - an iterable of ProductInsight objects or dict (if `as_dict=True`)
        - the number of products (if `count=True`)
        - a iterable of objects or dict (if `as_dict=True`) containing product
          count for each `value_tag`, if `group_by_value_tag=True`
    """
    where_clauses = [ProductInsight.server_type == server_type.name]

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

    if keep_types is not None:
        where_clauses.append(ProductInsight.type.in_(keep_types))

    if countries is not None:
        where_clauses.append(
            ProductInsight.countries.contains_any(
                [COUNTRY_CODE_TO_NAME[c] for c in countries]
            )
        )

    if brands:
        where_clauses.append(ProductInsight.brands.contains_any(brands))

    if reserved_barcode is not None:
        where_clauses.append(ProductInsight.reserved_barcode == reserved_barcode)

    if campaigns is not None:
        where_clauses.append(ProductInsight.campaign.contains_all(campaigns))

    if predictor is not None:
        where_clauses.append(ProductInsight.predictor == predictor)

    if lc is not None:
        where_clauses.append(ProductInsight.lc.contains_any(*lc))
    
    if with_image is not None:
        where_clauses.append(ProductInsight.source_image.is_null(not with_image))

    if avoid_voted_on:
        where_clauses.append(_add_vote_exclusion_clause(avoid_voted_on))

    query = ProductInsight.select()
    if where_clauses:
        query = query.where(*where_clauses)

    if count:
        if max_count is not None:
            query = query.limit(max_count)
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
    server_type: ServerType,
    with_predictions: bool | None = False,
    barcode: str | None = None,
    offset: int | None = None,
    count: bool = False,
    limit: int | None = None,
) -> Iterable[ImageModel]:
    where_clauses = [ImageModel.server_type == server_type.name]

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

    if limit is not None:
        query = query.limit(limit)

    if offset is not None:
        query = query.offset(offset)

    if count:
        return query.count()
    else:
        return query.iterator()


def get_predictions(
    server_type: ServerType,
    barcode: str | None = None,
    keep_types: list[str] | None = None,
    value_tag: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    count: bool = False,
) -> Iterable[Prediction]:
    where_clauses = [Prediction.server_type == server_type.name]

    if barcode:
        where_clauses.append(Prediction.barcode == barcode)

    if value_tag:
        where_clauses.append(Prediction.value_tag == value_tag)

    if keep_types:
        where_clauses.append(Prediction.type.in_(keep_types))

    query = Prediction.select()

    if where_clauses:
        query = query.where(*where_clauses)

    if limit is not None:
        query = query.limit(limit)

    if offset is not None:
        query = query.offset(offset)

    if count:
        return query.count()
    else:
        return query.iterator()


def get_image_predictions(
    server_type: ServerType,
    with_logo: bool | None = False,
    barcode: str | None = None,
    type: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    min_confidence: float | None = None,
    image_id: str | None = None,
    offset: int | None = None,
    count: bool = False,
    limit: int | None = None,
) -> Iterable[ImagePrediction]:
    query = ImagePrediction.select()

    query = query.switch(ImagePrediction).join(ImageModel)
    where_clauses = [ImagePrediction.image.server_type == server_type.name]

    if image_id is not None:
        where_clauses.append(ImagePrediction.image.image_id == image_id)

    if barcode is not None:
        where_clauses.append(ImagePrediction.image.barcode == barcode)

    if type is not None:
        where_clauses.append(ImagePrediction.type == type)

    if model_name is not None:
        where_clauses.append(ImagePrediction.model_name == model_name)

    if model_version is not None:
        where_clauses.append(ImagePrediction.model_version == model_version)

    if min_confidence is not None:
        where_clauses.append(ImagePrediction.max_confidence >= min_confidence)

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

    if limit is not None:
        query = query.limit(limit)

    if offset is not None:
        query = query.offset(offset)

    if count:
        return query.count()
    else:
        return query.iterator()


def save_annotation(
    insight_id: str,
    annotation: InsightAnnotation,
    device_id: str,
    update: bool = True,
    data: dict | None = None,
    auth: OFFAuthentication | None = None,
    trusted_annotator: bool = False,
) -> AnnotationResult:
    """Saves annotation either by using a single response as ground truth or
    by using several responses.

    If annotation == -1 (ignore), we consider the annotation as a vote, so that
    we don't return the insight to the user again. If there are >= 2 votes on
    one of the 2 other possible values (0/1), including the vote in process, we
    set the annotation value of the largest voting group. The only exception is
    when both groups >= 2 votes, in which case we mark the insight as invalid
    (annotation=-1). Note that `annotation=-1` has two different meanings here:
    if it's a vote, we consider it as a "ignore", and if it's the insight
    annotation value we consider the insight as invalid, so that it's not
    available for annotation again.

    :param insight_id: The ID of the insight
    :param annotation: The annotation, either -1, 0, 1 or 2
    :param device_id: Unique identifier of the device, see
      `device_id_from_request`
    :param update: If True, perform the update on Product Opener if
      annotation=1, otherwise only save the annotation (default: True)
    :param data: Optional additional data, required for some insight types
    :param auth: User authentication data, it is expected to be None if
        `trusted_annotator=False` (=anonymous vote)
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
            # If the top annotation has 3 or more votes, consider applying it
            # to the insight.
            if existing_votes[0].num_votes >= 3:
                annotation = existing_votes[0].value
                verified = True

            # But first check for the following cases:
            #  1) The 1st place annotation has > 2 votes, and the 2nd place
            #     annotation has >= 2 votes.
            #  2) 1st place and 2nd place have 2 votes each.
            #
            # In both cases, we consider this an ambiguous result and mark it
            # with 'I don't know'.
            if (
                existing_votes[0].num_votes >= 2
                and len(existing_votes) > 1
                and existing_votes[1].num_votes >= 2
            ):
                # This code credits the last person to contribute a vote with
                # a potentially not their annotation.
                annotation = -1
                verified = True

        if not verified:
            return SAVED_ANNOTATION_VOTE_RESULT

    result = annotate(
        insight, annotation, update, data=data, auth=auth, is_vote=not trusted_annotator
    )
    username = auth.get_username() if auth else "unknown annotator"
    events.event_processor.send_async(
        "question_answered",
        username,
        device_id,
        insight.barcode,
        insight.server_type,
    )
    return result


def get_logo_annotation(
    server_type: ServerType,
    barcode: str | None = None,
    keep_types: list[str] | None = None,
    value_tag: str | None = None,
    limit: int | None = 25,
    offset: int | None = None,
    count: bool = False,
) -> Iterable[LogoAnnotation]:
    """Return logos that fit the criteria passed as parameters.

    :param server_type: the server type (project) associated with the logos
    :param barcode: the barcode of the product associated with the logos,
        defaults to None (no barcode filter)
    :param keep_types: the list of logo types to keep, defaults to None (no
        type filter)
    :param value_tag: the annotation value tag to filter on, defaults to None
        (no value tag filter)
    :param limit: maximum number of logos to return, defaults to 25
    :param offset: offset for pagination, defaults to None (page 1)
    :param count: if True, return the number of logos instead of the logos,
        defaults to False
    :return: either the number of logos (if `count=True`) or an iterable of
        logos
    """
    query = LogoAnnotation.select().join(ImagePrediction).join(ImageModel)

    where_clauses = [
        ImageModel.server_type == server_type.name,
        ImageModel.deleted == False,  # noqa
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
    annotation_logos: list[tuple[str, str | None, LogoAnnotation]],
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


def filter_question_insight_types(keep_types: list[str] | None):
    """Utility function to validate `insight_types` parameters in /questions/*
    queries.

    If `keep_types` is None, we return default question types.
    If `keep_types` is not None, we only keep valid types.

    :param keep_types: the input `insight_types` list
    :return: the sanitized `insight_types` list
    """
    if keep_types is None:
        keep_types = QuestionFormatterFactory.get_default_types()
    else:
        keep_types = list(
            set(keep_types) & set(QuestionFormatterFactory.get_available_types())
        )
    return keep_types


def validate_params(params: JSONType, schema: type) -> BaseModel:
    """Validate the parameters passed to a Falcon resource.

    Either returns a validated params object or raises a falcon.HTTPBadRequest.

    :param params: the input parameters to validate, as a dict
    :param schema: the pydantic schema to use for validation
    :raises falcon.HTTPBadRequest: if the parameters are invalid
    """
    # Remove None values from the params dict
    params = {k: v for k, v in params.items() if v is not None}
    try:
        return schema.model_validate(params)  # type: ignore
    except ValidationError as e:
        errors = e.errors(include_url=False)
        plural = "s" if len(errors) > 1 else ""
        description = f"{len(errors)} validation error{plural}: {errors}"
        raise falcon.HTTPBadRequest(description=description)
