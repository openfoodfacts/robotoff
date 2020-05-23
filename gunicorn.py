from robotoff import models

bind = ":5500"
workers = 4
preload_app = True
timeout = 60


def on_starting(server):
    """Gunicorn server hook."""
    with models.db:
        models.db.create_tables(models.MODELS, safe=True)
