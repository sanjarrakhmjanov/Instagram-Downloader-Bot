import logging
import sys

from pythonjsonlogger import jsonlogger


def setup_json_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(filename)s %(funcName)s %(lineno)d"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

