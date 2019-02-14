import subprocess

import click
from robotoff import settings


def run(service: str):
    if service == 'api':
        subprocess.run(["gunicorn", "--config",
                        str(settings.PROJECT_DIR / "gunicorn.conf"),
                        "robotoff.app.api:api"])

    elif service == 'workers':
        from robotoff.workers import listener

        listener.run()

    else:
        click.echo("invalid service: '{}'".format(service), err=True)
