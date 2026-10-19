import datetime
import logging

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from peewee import fn

from robotoff import settings
from robotoff.models import ProductInsight, with_db

logger = logging.getLogger(__name__)


def get_influx_client() -> InfluxDBClient | None:
    if not settings.INFLUXDB_HOST:
        return None
    return InfluxDBClient(
        url=f"http://{settings.INFLUXDB_HOST}:{settings.INFLUXDB_PORT}",
        token=settings.INFLUXDB_AUTH_TOKEN,
        org=settings.INFLUXDB_ORG,
    )


def ensure_influx_database():
    client = get_influx_client()
    if client is not None:
        try:
            bucket_client = client.buckets_api()
            bucket_names = [
                bucket.name for bucket in bucket_client.find_buckets().buckets
            ]
            if settings.INFLUXDB_BUCKET not in bucket_names:
                # create it
                client.bucket_name(bucket_name=settings.INFLUXDB_BUCKET)
                logger.warning(
                    "Creating influxdb bucket %r as it does not exist yet",
                    settings.INFLUXDB_BUCKET,
                )
        except Exception:
            # better be fail safe, our job is not that important !
            logger.exception("Error on ensure_influx_database")


def save_insight_metrics():
    """Save number of insights, grouped by the following fields:
    - type
    - annotation
    - automatic_processing
    - predictor
    - reserved_barcode
    - server_type
    """
    target_datetime = datetime.datetime.now()

    if (client := get_influx_client()) is not None:
        write_client = client.write_api(write_options=SYNCHRONOUS)
        inserts = generate_insight_metrics(target_datetime)
        write_client.write(bucket=settings.INFLUXDB_BUCKET, record=inserts)


@with_db
def generate_insight_metrics(target_datetime: datetime.datetime) -> list[dict]:
    group_by_fields = [
        ProductInsight.type,
        ProductInsight.annotation,
        ProductInsight.automatic_processing,
        ProductInsight.predictor,
        ProductInsight.reserved_barcode,
        ProductInsight.server_type,
    ]
    inserts = []
    query_results = (
        ProductInsight.select(
            *group_by_fields,
            fn.COUNT(ProductInsight.id).alias("count"),
        )
        .group_by(*group_by_fields)
        .dicts()
    )
    total_count = sum(query_result["count"] for query_result in query_results)

    for query_result in query_results:
        count = query_result.pop("count")
        inserts.append(
            {
                "measurement": "insights",
                "tags": query_result,
                "time": target_datetime.isoformat(),
                "fields": {"count": count, "percent": count / total_count},
            }
        )
    return inserts
