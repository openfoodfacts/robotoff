from typing import Optional

import click


@click.group()
def cli():
    pass


@click.command()
@click.argument('service')
def run(service: str):
    from robotoff.cli.run import run as run_
    run_(service)


@click.command()
@click.argument('input_')
@click.option('--insight-type', required=True)
@click.option('--output', '-o')
def generate_insights(input_: str, insight_type: str, output: str):
    from robotoff.cli import insights
    insights.run(input_, insight_type, output)


@click.command()
@click.option('--insight-type')
@click.option('--country')
def annotate(insight_type: Optional[str], country: Optional[str]):
    from robotoff.cli import annotate as annotate_
    annotate_.run(insight_type, country)


@click.command()
@click.option('--insight-type', required=True)
@click.option('--dry/--no-dry', default=True)
@click.option('-f', '--filter', 'filter_clause')
def batch_annotate(insight_type: str, dry: bool, filter_clause: str):
    from robotoff.cli import batch
    batch.run(insight_type, dry, filter_clause)


cli.add_command(run)
cli.add_command(generate_insights)
cli.add_command(annotate)
cli.add_command(batch_annotate)


if __name__ == '__main__':
    cli()
