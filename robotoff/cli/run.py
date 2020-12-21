import subprocess

import click

from robotoff import settings


def run(service: str):
    if service == "api":
        subprocess.run(
            [
                "gunicorn",
                "--config",
                str(settings.PROJECT_DIR / "gunicorn.py"),
                "robotoff.app.api:api",
            ]
        )

    elif service == "workers":
        from robotoff.workers import listener

        listener.run()

    elif service == "scheduler":
        from robotoff import scheduler
        from robotoff.utils import get_logger

        # Defining a root logger
        get_logger()
        scheduler.run()

    else:
        click.echo("invalid service: '{}'".format(service), err=True)
