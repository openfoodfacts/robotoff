import logging
import os
import sys


def get_logger(name=None, level: int | None = None):
    logger = logging.getLogger(name)

    if level is None:
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = logging.getLevelName(log_level)

        if not isinstance(level, int):
            print(
                f"Unknown log level: {log_level}, fallback to INFO",
                file=sys.stderr,
            )
            level = 20

    logger.setLevel(level)

    if name is None:
        configure_root_logger(logger, level)

    return logger


def configure_root_logger(logger, level: int = 20):
    logger.setLevel(level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s :: pid %(process)d :: "
        "%(threadName)s :: %(levelname)s :: "
        "%(message)s"
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)

    for name in ("redis_lock",):
        logging.getLogger(name).setLevel(logging.WARNING)
