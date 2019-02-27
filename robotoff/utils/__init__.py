import gzip
import json
import logging
import os
import pathlib
import sys
from typing import Union, Iterable, Dict


def get_logger(name=None, level: str = "INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if name is None:
        configure_root_logger(logger, level)

    return logger


def configure_root_logger(logger, level: str = "INFO"):
    log_level = os.environ.get('LOG_LEVEL', "INFO").upper()

    if log_level not in (
            "DEBUG", "INFO", "WARNING", "ERROR", "FATAL", "CRITICAL"):
        print("Unknown log level: {}, fallback "
              "to INFO".format(log_level), file=sys.stderr)
        log_level = level

    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s :: %(processName)s :: '
                                  '%(threadName)s :: %(levelname)s :: '
                                  '%(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger.addHandler(handler)


def jsonl_iter(jsonl_path: Union[str, pathlib.Path]) -> Iterable[Dict]:
    with open(jsonl_path, 'r') as f:
        yield from jsonl_iter_fp(f)


def gzip_jsonl_iter(jsonl_path: Union[str, pathlib.Path]) -> Iterable[Dict]:
    with gzip.open(jsonl_path, 'rt') as f:
        yield from jsonl_iter_fp(f)


def jsonl_iter_fp(fp) -> Iterable[Dict]:
    for line in fp:
        line = line.strip('\n')
        if line:
            yield json.loads(line)


def dump_jsonl(filepath: Union[str, pathlib.Path],
               json_iter: Iterable[Dict]):
    with open(str(filepath), 'w') as f:
        for item in json_iter:
            f.write(json.dumps(item) + "\n")
