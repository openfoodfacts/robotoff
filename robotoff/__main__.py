if __name__ == "__main__":
    import pathlib
    from typing import Optional

    import click

    @click.group()
    def cli():
        pass

    @click.command()
    @click.argument("service")
    def run(service: str):
        from robotoff.cli.run import run as run_

        run_(service)

    @click.command()
    @click.argument("ocr_url")
    def predict_insight(ocr_url: str):
        import json
        from robotoff.insights.extraction import (
            extract_ocr_insights,
            DEFAULT_INSIGHT_TYPES,
        )
        from robotoff.utils import get_logger

        get_logger()

        results = extract_ocr_insights(ocr_url, DEFAULT_INSIGHT_TYPES)

        print(json.dumps(results, indent=4))

    @click.command()
    @click.argument("input_")
    @click.option("--insight-type", "-t", required=True)
    @click.option("--output", "-o")
    @click.option(
        "--keep-empty/--no-keep-empty",
        default=False,
        help="keep documents with empty insight",
    )
    def generate_ocr_insights(
        input_: str, insight_type: str, output: str, keep_empty: bool
    ):
        from robotoff.cli import insights
        from robotoff.utils import get_logger

        get_logger()
        insights.run_from_ocr_archive(input_, insight_type, output, keep_empty)

    @click.command()
    @click.option("--insight-type")
    @click.option("--country")
    def annotate(insight_type: Optional[str], country: Optional[str]):
        from robotoff.cli import annotate as annotate_

        annotate_.run(insight_type, country)

    @click.command()
    @click.option("--insight-type", required=True)
    @click.option("--dry/--no-dry", default=True)
    @click.option("-f", "--filter", "filter_clause")
    def batch_annotate(insight_type: str, dry: bool, filter_clause: str):
        from robotoff.cli import batch

        batch.run(insight_type, dry, filter_clause)

    @click.command()
    @click.argument("output")
    def predict_category(output: str):
        from robotoff.elasticsearch.category.predict import predict_from_dataset
        from robotoff.utils import dump_jsonl
        from robotoff.products import ProductDataset
        from robotoff import settings

        dataset = ProductDataset(settings.JSONL_DATASET_PATH)
        dump_jsonl(output, predict_from_dataset(dataset))

    @click.command()
    @click.argument("pattern")
    @click.argument("correction")
    @click.option("--country", default="fr")
    @click.option("--username", required=True, prompt="Username")
    @click.option("--password", required=True, prompt="Password", hide_input=True)
    @click.option("--dry/--no-dry", default=False)
    def spellcheck(
        pattern: str,
        correction: str,
        country: str,
        username: str,
        password: str,
        dry: bool,
    ):
        from robotoff.cli.spellcheck import correct_ingredient
        from robotoff.insights.ocr.utils import get_tag
        from robotoff.utils import get_logger
        from robotoff.off import OFFAuthentication

        get_logger()
        ingredient = get_tag(pattern)
        comment = "Fixing '{}' typo".format(pattern)
        auth = OFFAuthentication(username=username, password=password)
        correct_ingredient(
            country, ingredient, pattern, correction, comment, dry_run=dry, auth=auth
        )

    @click.command()
    @click.argument("output", type=pathlib.Path)
    @click.option("--confidence", type=float, default=1)
    @click.option("--max-errors", type=int)
    def generate_spellcheck_insights(
        output: str, confidence: float, max_errors: Optional[int] = None
    ):
        from robotoff.utils import dump_jsonl
        from robotoff.utils.es import get_es_client
        from robotoff.ingredients import generate_insights
        from robotoff.utils import get_logger

        logger = get_logger()
        logger.info("Max errors: {}".format(max_errors))

        client = get_es_client()
        insights_iter = generate_insights(
            client, confidence=confidence, max_errors=max_errors
        )
        dump_jsonl(output, insights_iter)

    @click.command()
    @click.argument("text")
    @click.option("--confidence", type=float, default=1)
    def test_spellcheck(text: str, confidence: float):
        import json
        from robotoff.utils.es import get_es_client
        from robotoff.ingredients import suggest
        from robotoff.utils import get_logger

        get_logger()
        client = get_es_client()
        result = suggest(text, client, confidence=confidence)
        print(json.dumps(result, indent=5))

    @click.command()
    @click.option("--minify/--no-minify", default=False)
    def download_dataset(minify: bool):
        from robotoff.products import has_dataset_changed, fetch_dataset
        from robotoff.utils import get_logger

        get_logger()

        if has_dataset_changed():
            fetch_dataset(minify)

    @click.command()
    @click.argument("barcode")
    @click.option("--deepest-only/--all-categories", default=False)
    @click.option("--blacklist/--no-blacklist", default=False)
    def categorize(barcode: str, deepest_only: bool, blacklist: bool):
        from robotoff.ml.category.neural.model import (
            LocalModel,
            filter_blacklisted_categories,
        )
        from robotoff import settings
        from robotoff.utils import get_logger

        get_logger()
        model = LocalModel(settings.CATEGORY_CLF_MODEL_PATH)
        predicted = model.predict_from_barcode(barcode, deepest_only=deepest_only)

        if predicted:
            if blacklist:
                predicted = filter_blacklisted_categories(predicted)

            for cat, confidence in predicted:
                print("{}: {}".format(cat, confidence))

    @click.command()
    @click.argument("input_", type=pathlib.Path)
    @click.option("--insight-type", required=True)
    @click.option("--server-domain", default=None)
    @click.option("--batch-size", type=int, default=1024)
    def import_insights(
        input_: pathlib.Path,
        insight_type: str,
        server_domain: Optional[str],
        batch_size: int,
    ):
        from robotoff.cli import insights
        from robotoff import settings
        from robotoff.utils import get_logger

        logger = get_logger()
        logger.info("Importing insights from {}".format(input_))
        server_domain = server_domain or settings.OFF_SERVER_DOMAIN
        imported = insights.import_insights(
            input_, insight_type, server_domain, batch_size
        )
        logger.info("{} insights imported".format(imported))

    @click.command()
    @click.option("--index/--no-index", default=False)
    @click.option("--data/--no-data", default=True)
    @click.option("--product/--no-product", default=False)
    @click.option("--category/--no-category", default=False)
    @click.option("--product-version", default="product")
    def init_elasticsearch(
        index: bool, data: bool, product: bool, category: bool, product_version: str
    ):
        import json
        from robotoff import settings
        from robotoff.utils.es import get_es_client
        from robotoff.elasticsearch.product.dump import product_export
        from robotoff.elasticsearch.category.dump import category_export

        if index:
            with settings.ELASTICSEARCH_PRODUCT_INDEX_CONFIG_PATH.open("r") as f:
                product_index_config = json.load(f)

            with settings.ELASTICSEARCH_CATEGORY_INDEX_CONFIG_PATH.open("r") as f:
                category_index_config = json.load(f)

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

    cli.add_command(run)
    cli.add_command(generate_ocr_insights)
    cli.add_command(annotate)
    cli.add_command(batch_annotate)
    cli.add_command(predict_category)
    cli.add_command(init_elasticsearch)
    cli.add_command(spellcheck)
    cli.add_command(generate_spellcheck_insights)
    cli.add_command(test_spellcheck)
    cli.add_command(download_dataset)
    cli.add_command(categorize)
    cli.add_command(import_insights)
    cli.add_command(predict_insight)

    cli()
