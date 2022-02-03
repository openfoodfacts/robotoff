import os

from robotoff import models

bind = ":5500"
# we have a trade-off with memory vs cpu numbers
workers = int(os.environ.get("GUNICORN_NUM_WORKERS", 4))
worker_connections = 1000
preload_app = True
timeout = 60


def on_starting(server):
    """Gunicorn server hook."""
    with models.db:
        models.db.create_tables(models.MODELS, safe=True)
