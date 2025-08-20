import logging
import os


class EnvvarLogFilter(logging.Filter):
    """A filter that filters out log messages based on environment variables."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "robotoff.ml_metrics":
            # only allow log records from the robotoff.ml_metrics logger if the
            # environment variable is set LOG_ML_METRICS_ENABLED is set to 1
            return bool(int(os.environ.get("LOG_ML_METRICS_ENABLED", 0) or 0))
        # otherwise, allow the log record
        return True


def get_logger(name=None, level: str | int | None = None):
    logger = logging.getLogger(name)

    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()

    logger.setLevel(level)

    if name is None:
        configure_root_logger(logger, level)

    return logger


def configure_root_logger(logger, level: str | int = logging.INFO):
    logger.setLevel(level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s :: pid %(process)d :: "
        "%(threadName)s :: %(levelname)s :: "
        "%(message)s"
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    handler.addFilter(EnvvarLogFilter())
    logger.addHandler(handler)

    for name in ("redis_lock",):
        logging.getLogger(name).setLevel(logging.WARNING)
