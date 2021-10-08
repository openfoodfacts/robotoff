import multiprocessing

from robotoff import models

bind = ":5500"
workers = multiprocessing.cpu_count() * 2 + 1
worker_connections = 1000
preload_app = True
timeout = 60


def on_starting(server):
    """Gunicorn server hook."""
    with models.db:
        models.db.create_tables(models.MODELS, safe=True)
