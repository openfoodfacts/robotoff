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
    # Perform migrations
    with models.db.connection_context():
        models.run_migration()
