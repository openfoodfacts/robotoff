import os

bind = ":5500"
# we have a trade-off with memory vs cpu numbers
workers = int(os.environ.get("GUNICORN_NUM_WORKERS", 4))
worker_connections = 1000
# gunicorn --auto-reload is not compatible with preload_app
# so it has to be disabled when developing
# Default to True (production) if not specified
preload_app = bool(os.environ.get("GUNICORN_PRELOAD_APP", True))
timeout = 60
# Limit the impact of caching on RAM use by restarting workers
# every 500 requests
max_requests = 500
max_requests_jitter = 50
