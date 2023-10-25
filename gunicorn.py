import os

bind = ":5500"
# we have a trade-off with memory vs cpu numbers
workers = int(os.environ.get("GUNICORN_NUM_WORKERS", 4))
worker_connections = 1000
preload_app = True
timeout = 60
