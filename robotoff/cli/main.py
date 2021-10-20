import pathlib
import sys
from pathlib import Path
from typing import Optional

import typer
from typer import Argument, Option

app = typer.Typer()


@app.command()
def run(service: str) -> None:
    from robotoff.cli.run import run as run_

    run_(service)


@app.command()
def predict_insight(ocr_url: str) -> None:
    import json

    from robotoff.insights.extraction import DEFAULT_INSIGHT_TYPES, extract_ocr_insights
    from robotoff.utils import get_logger

    get_logger()

    results = extract_ocr_insights(ocr_url, DEFAULT_INSIGHT_TYPES)

    print(json.dumps(results, indent=4))


@app.command()
def generate_ocr_insights(
    source: str,
    insight_type: str,
    output: Path = Option(
        ...,
        help="File to write output to, stdout if not specified",
        dir_okay=False,
        writable=True,
    ),
    keep_empty: bool = Argument(..., help="Keep documents with empty insight"),
) -> None:
    """Generate OCR insights of the requested type.

    SOURCE can be either:
    * the path to a JSON file, a (gzipped-)JSONL file, or a directory
        containing JSON files
    * a barcode
    * the '-' character: input is read from stdin and assumed to be JSONL

    Output is JSONL, each line containing the insights for one document.
    """
    from typing import TextIO, Union

    from robotoff.cli import insights
    from robotoff.insights._enum import InsightType
    from robotoff.utils import get_logger

    input_: Union[str, TextIO] = sys.stdin if source == "-" else source

    get_logger()
    insights.run_from_ocr_archive(input_, InsightType[insight_type], output, keep_empty)


@app.command()
def annotate(insight_type: Optional[str], country: Optional[str]) -> None:
    from robotoff.cli import annotate as annotate_

    annotate_.run(insight_type, country)


@app.command()
def batch_annotate(insight_type: str, filter_clause: str, dry: bool = True) -> None:
    from robotoff.cli import batch

    batch.run(insight_type, dry, filter_clause)


@app.command()
def predict_category(output: str) -> None:
    from robotoff import settings
    from robotoff.elasticsearch.category.predict import predict_from_dataset
    from robotoff.products import ProductDataset
    from robotoff.utils import dump_jsonl

    dataset = ProductDataset(settings.JSONL_DATASET_PATH)
    insights = predict_from_dataset(dataset)
    dict_insights = (i.to_dict() for i in insights)
    dump_jsonl(output, dict_insights)


@app.command()
def spellcheck(
    pattern: str,
    correction: str,
    country: str = "fr",
    dry: bool = False,
) -> None:
    from robotoff.cli.spellcheck import correct_ingredient
    from robotoff.off import OFFAuthentication
    from robotoff.utils import get_logger
    from robotoff.utils.text import get_tag

    username = typer.prompt("Username ?")
    password = typer.prompt("Password ?", hide_input=True)

    get_logger()
    ingredient = get_tag(pattern)
    comment = "Fixing '{}' typo".format(pattern)
    auth = OFFAuthentication(username=username, password=password)
    correct_ingredient(
        country, ingredient, pattern, correction, comment, dry_run=dry, auth=auth
    )


@app.command()
def generate_spellcheck_insights(
    output: str,
    index_name: str = "product_all",
    confidence: float = 0.5,
    max_errors: Optional[int] = None,
    limit: Optional[int] = None,
) -> None:
    from robotoff.spellcheck import Spellchecker
    from robotoff.utils import dump_jsonl, get_logger
    from robotoff.utils.es import get_es_client

    logger = get_logger()
    logger.info("Max errors: {}".format(max_errors))

    client = get_es_client()
    insights_iter = Spellchecker.load(
        client=client, confidence=confidence, index_name=index_name
    ).generate_insights(max_errors=max_errors, limit=limit)

    dump_jsonl(output, insights_iter)


@app.command()
def test_spellcheck(text: str, confidence: float = 1.0) -> None:
    import json

    from robotoff.spellcheck import Spellchecker
    from robotoff.utils import get_logger
    from robotoff.utils.es import get_es_client

    get_logger()
    client = get_es_client()
    result = Spellchecker.load(client=client, confidence=confidence).predict_insight(
        text, detailed=True
    )
    print(json.dumps(result, indent=5))


@app.command()
def download_dataset(minify: bool = False) -> None:
    from robotoff.products import fetch_dataset, has_dataset_changed
    from robotoff.utils import get_logger

    get_logger()

    if has_dataset_changed():
        fetch_dataset(minify)


@app.command()
def download_models(force: bool = False) -> None:
    """Download model weights from remote URLs.

    If models have already been downloaded, the command is skipped unless
    --force option is used.

    TODO: add all models to this CLI.
    """
    from robotoff.cli.file import download_file
    from robotoff.ml.category.prediction_from_ocr.constants import (
        RIDGE_PREDICTOR_FILEPATH,
        RIDGE_PREDICTOR_URL,
    )
    from robotoff.utils import get_logger

    get_logger()

    download_file(
        url=RIDGE_PREDICTOR_URL,
        destination=RIDGE_PREDICTOR_FILEPATH,
        force=force,
    )


@app.command()
def categorize(
    barcode: str,
    deepest_only: bool = False,
    blacklist: bool = False,
) -> None:
    from robotoff import settings
    from robotoff.ml.category.neural.model import (
        LocalModel,
        filter_blacklisted_categories,
    )
    from robotoff.utils import get_logger

    get_logger()
    model = LocalModel(settings.CATEGORY_CLF_MODEL_PATH)
    predicted = model.predict_from_barcode(barcode, deepest_only=deepest_only)

    if predicted:
        if blacklist:
            predicted = filter_blacklisted_categories(predicted)

        for cat, confidence in predicted:
            print("{}: {}".format(cat, confidence))


@app.command()
def import_insights(
    insight_type: Optional[str],
    server_domain: Optional[str] = None,
    batch_size: int = 1024,
    input_: Optional[pathlib.Path] = None,
    generate_from: Optional[pathlib.Path] = None,
) -> None:
    """This command is used to backfill a new insight type on the daily product data dump."""
    from robotoff import settings
    from robotoff.cli.insights import generate_from_ocr_archive
    from robotoff.cli.insights import import_insights as import_insights_
    from robotoff.cli.insights import insights_iter
    from robotoff.insights._enum import InsightType
    from robotoff.utils import get_logger

    logger = get_logger()
    server_domain = server_domain or settings.OFF_SERVER_DOMAIN

    if generate_from is not None:
        logger.info("Generating and importing insights from {}".format(generate_from))
        if insight_type is None:
            sys.exit("Required option: --insight-type")

        insights = generate_from_ocr_archive(generate_from, InsightType[insight_type])
    elif input_ is not None:
        logger.info("Importing insights from {}".format(input_))
        insights = insights_iter(input_)
    else:
        raise ValueError("--generate-from or --input must be provided")

    imported = import_insights_(insights, server_domain, batch_size)
    logger.info("{} insights imported".format(imported))


@app.command()
def apply_insights(
    insight_type: str,
    delta: int = 1,
) -> None:
    import datetime

    from robotoff.cli import insights
    from robotoff.utils import get_logger

    logger = get_logger()
    logger.info("Applying {} insights".format(insight_type))
    insights.apply_insights(insight_type, datetime.timedelta(days=delta))


@app.command()
def init_elasticsearch(
    index: bool = False,
    data: bool = True,
    product: bool = False,
    category: bool = False,
    product_version: str = "product",
) -> None:
    """
    This command is used for manual insertion of the Elasticsearch data and/or indexes
    for products and categorties.
    """
    import orjson

    from robotoff import settings
    from robotoff.elasticsearch.category.dump import category_export
    from robotoff.elasticsearch.product.dump import product_export
    from robotoff.utils.es import get_es_client

    if index:
        with settings.ELASTICSEARCH_PRODUCT_INDEX_CONFIG_PATH.open("rb") as f:
            product_index_config = orjson.loads(f.read())

        with settings.ELASTICSEARCH_CATEGORY_INDEX_CONFIG_PATH.open("rb") as f:
            category_index_config = orjson.loads(f.read())

        client = get_es_client()

        if product:
            client.indices.create(product_version, product_index_config)

        if category:
            client.indices.create("category", category_index_config)

    if data:
        if product:
            product_export(version=product_version)

        if category:
            category_export()


@app.command()
def add_logo_to_ann(sleep_time: float = 0.5) -> None:
    import time
    from itertools import groupby

    import requests
    import tqdm

    from robotoff.logos import add_logos_to_ann, get_stored_logo_ids
    from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
    from robotoff.utils import get_logger

    logger = get_logger()
    seen = get_stored_logo_ids()

    with db:
        logos_iter = tqdm.tqdm(
            LogoAnnotation.select()
            .join(ImagePrediction)
            .join(ImageModel)
            .where(LogoAnnotation.nearest_neighbors.is_null())
            .order_by(ImageModel.id)
            .iterator()
        )
        for _, logo_batch in groupby(logos_iter, lambda x: x.image_prediction.image.id):
            logos = list(logo_batch)

            if all(logo.id in seen for logo in logos):
                continue

            image = logos[0].image_prediction.image
            logger.info(f"Adding logos of image {image.id}")
            try:
                added = add_logos_to_ann(image, logos)
            except requests.exceptions.ReadTimeout:
                logger.warn("Request timed-out during logo addition")
                continue

            logger.info(f"Added: {added}")

            if sleep_time:
                time.sleep(sleep_time)


@app.command()
def import_logos(
    data_path: pathlib.Path,
    model_name: str = "universal-logo-detector",
    model_version: str = "tf-universal-logo-detector-1.0",
) -> None:
    from robotoff.cli.logos import insert_batch
    from robotoff.models import db
    from robotoff.utils import get_logger

    logger = get_logger()
    logger.info("Starting image prediction import...")

    with db:
        inserted = insert_batch(data_path, model_name, model_version)

    logger.info("{} image predictions inserted".format(inserted))


@app.command()
def export_logo_annotation(
    output: pathlib.Path,
    server_domain: Optional[str] = None,
    annotated: Optional[bool] = None,
) -> None:
    from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
    from robotoff.utils import dump_jsonl

    with db:
        where_clauses = []

        if server_domain is not None:
            where_clauses.append(ImageModel.server_domain == server_domain)

        if annotated is not None:
            where_clauses.append(LogoAnnotation.annotation_value.is_null(not annotated))

        query = LogoAnnotation.select().join(ImagePrediction).join(ImageModel)
        if where_clauses:
            query = query.where(*where_clauses)

        logo_iter = query.iterator()
        dict_iter = (logo.to_dict() for logo in logo_iter)
        dump_jsonl(output, dict_iter)


def main() -> None:
    app()
