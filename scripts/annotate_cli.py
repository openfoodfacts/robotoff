import json
from typing import Optional, Dict, Any
import click
import requests


http_session = requests.Session()

LOCAL = True

if LOCAL:
    BASE_URL = "http://localhost:5500/api/v1"
else:
    BASE_URL = "https://robotoff.openfoodfacts.org/api/v1"

RANDOM_INSIGHT_URL = BASE_URL + "/insights/random"
ANNOTATE_INSIGHT_URL = BASE_URL + "/insights/annotate"
STATIC_IMAGE_DIR_URL = "https://static.openfoodfacts.org/images/products"


class NoInsightException(Exception):
    pass


@click.command()
@click.option('--insight-type')
@click.option('--country')
def run(insight_type: Optional[str], country: Optional[str]):
    while True:
        try:
            run_loop(insight_type, country)
        except NoInsightException:
            click.echo("No insight left")


def run_loop(insight_type: Optional[str],
             country: Optional[str]) -> None:
    insight = get_random_insight(insight_type, country)
    print_insight(insight)

    annotation = None

    while annotation is None:
        annotation = click.prompt('Annotation [-1, 0, 1]: ', type=int)

        if annotation not in (0, 1, -1):
            click.echo("Invalid value: 0, 1 or -1 expected", err=True)
            annotation = None

    response = save_insight(insight['id'], annotation=annotation)
    click.echo(json.dumps(response, indent=4) + "\n")


def get_random_insight(insight_type: Optional[str] = None,
                       country: Optional[str] = None) -> Dict[str, Any]:
    params = {}

    if insight_type:
        params['type'] = insight_type

    if country:
        params['country'] = country

    r = http_session.get(RANDOM_INSIGHT_URL, params=params)
    data = r.json()

    if data['status'] == 'no_insights':
        raise NoInsightException()

    return data['insight']


def save_insight(insight_id: str, annotation: int):
    params = {
        'insight_id': insight_id,
        'annotation': annotation,
    }

    r = http_session.post(ANNOTATE_INSIGHT_URL, data=params)
    data = r.json()

    return data


def print_insight(insight: Dict[str, Any]) -> None:
    for key, value in insight.items():
        click.echo('{}: {}'.format(key, str(value)))

    click.echo("url: {}".format("https://fr.openfoodfacts.org/produit/"
                                "{}".format(insight['barcode'])))

    if 'source' in insight:
        click.echo("image: {}{}".format(STATIC_IMAGE_DIR_URL,
                                        insight['source']))
    click.echo("")


if __name__ == "__main__":
    run()
