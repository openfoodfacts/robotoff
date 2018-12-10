import logging
import os
import sys


def get_logger(name=None, level="INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if name is None:
        log_level = os.environ.get('LOG_LEVEL', "INFO").upper()

        if log_level not in (
                "DEBUG", "INFO", "WARNING", "ERROR", "FATAL", "CRITICAL"):
            print("Unknown log level: {}, fallback "
                  "to INFO".format(log_level), file=sys.stderr)
            log_level = level

        logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s :: '
                                      '%(levelname)s :: %(message)s')
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
        logger.addHandler(handler)

    return logger
