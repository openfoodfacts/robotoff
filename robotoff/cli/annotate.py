import json
from difflib import SequenceMatcher
from typing import Dict, Optional

import click

from robotoff import settings
from robotoff.utils import http_session
from robotoff.utils.types import JSONType

LOCAL = False

if LOCAL:
    BASE_URL = "http://localhost:5500/api/v1"
else:
    BASE_URL = settings.BaseURLProvider().robotoff().get() + "/api/v1"

RANDOM_INSIGHT_URL = BASE_URL + "/insights/random"
ANNOTATE_INSIGHT_URL = BASE_URL + "/insights/annotate"


class NoInsightException(Exception):
    pass


def run(insight_type: Optional[str], country: Optional[str]):
    while True:
        try:
            run_loop(insight_type, country)
        except NoInsightException:
            click.echo("No insight left")


def run_loop(insight_type: Optional[str], country: Optional[str]) -> None:
    insight = get_random_insight(insight_type, country)
    print_insight(insight)

    annotation = None

    while annotation is None:
        annotation = click.prompt("Annotation [-1, 0, 1]: ", type=int)

        if annotation not in (0, 1, -1):
            click.echo("Invalid value: 0, 1 or -1 expected", err=True)
            annotation = None

    response = save_insight(insight["id"], annotation=annotation)
    click.echo(json.dumps(response, indent=4) + "\n")


def get_random_insight(
    insight_type: Optional[str] = None, country: Optional[str] = None
) -> JSONType:
    params = {}

    if insight_type:
        params["type"] = insight_type

    if country:
        params["country"] = country

    r = http_session.get(RANDOM_INSIGHT_URL, params=params)
    data = r.json()

    if data["status"] == "no_insights":
        raise NoInsightException()

    return data["insight"]


def save_insight(insight_id: str, annotation: int):
    params = {
        "insight_id": insight_id,
        "annotation": str(annotation),
    }

    r = http_session.post(ANNOTATE_INSIGHT_URL, data=params)
    data = r.json()

    return data


def print_insight(insight: Dict) -> None:
    insight_type = insight.get("type")

    if insight_type == "ingredient_spellcheck":
        print_ingredient_spellcheck_insight(insight)

    else:
        print_generic_insight(insight)


def print_generic_insight(insight: JSONType) -> None:
    for key, value in insight.items():
        click.echo("{}: {}".format(key, str(value)))

    click.echo(
        "url: {}/product/{}".format(
            settings.BaseURLProvider().get(), insight["barcode"]
        )
    )

    if "source" in insight:
        click.echo("image: {}{}".format(settings.OFF_IMAGE_BASE_URL, insight["source"]))
    click.echo("")


def print_ingredient_spellcheck_insight(insight: JSONType) -> None:
    for key in ("id", "type", "barcode", "countries"):
        value = insight.get(key)
        click.echo("{}: {}".format(key, str(value)))

    click.echo(
        "url: {}/product/{}".format(
            settings.BaseURLProvider().get(), insight["barcode"]
        )
    )

    original_snippet = insight["original_snippet"]
    corrected_snippet = insight["corrected_snippet"]
    click.echo(generate_colored_diff(original_snippet, corrected_snippet))
    click.echo("")


def generate_colored_diff(original: str, correction: str) -> str:
    matcher = SequenceMatcher(None, original, correction)

    diff = ""
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            diff += original[i1:i2]
        elif opcode == "insert":
            diff += click.style(correction[j1:j2], fg="black", bg="green")
        elif opcode == "delete":
            diff += click.style(original[i1:i2], fg="black", bg="red")
        elif opcode == "replace":
            diff += click.style(original[i1:i2], fg="black", bg="red")
            diff += click.style(correction[j1:j2], fg="black", bg="green")

    return diff
