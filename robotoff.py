from typing import Optional

import click


@click.group()
def cli():
    pass


@click.command()
@click.argument('service')
def run(service: str):
    from robotoff.cli.run import run
    run(service)


@click.command()
@click.argument('input_')
@click.option('--insight-type', required=True)
@click.option('--output', '-o')
def generate_insights(input_: str, insight_type: str, output: str):
    from robotoff.cli.insights import run
    run(input_, insight_type, output)


@click.command()
@click.option('--insight-type')
@click.option('--country')
def annotate(insight_type: Optional[str], country: Optional[str]):
    from robotoff.cli.annotate import run
    run(insight_type, country)


cli.add_command(run)
cli.add_command(generate_insights)
cli.add_command(annotate)


if __name__ == '__main__':
    cli()
